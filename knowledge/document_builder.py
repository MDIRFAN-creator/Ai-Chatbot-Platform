"""Document Builder for SupportBot AI Knowledge Base.

Transforms structured domain models (Business, Product, Policy, FAQ)
into normalized LangChain Documents with validated metadata and length-aware chunking.
"""

from typing import List, Optional, Sequence, Union
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import get_config
from core.models import Business, BusinessCreate, FAQ, FAQCreate, Policy, PolicyCreate, Product, ProductCreate
from knowledge.metadata import create_document_metadata


def build_business_document(business: Union[Business, BusinessCreate]) -> Document:
    """Build a normalized LangChain Document for a business profile."""
    lines: List[str] = [
        f"Business Name: {business.name}",
    ]
    if business.description:
        lines.append(f"Description: {business.description}")
    if business.industry:
        lines.append(f"Industry: {business.industry}")
    if business.location:
        lines.append(f"Location: {business.location}")
    if business.website:
        lines.append(f"Website: {business.website}")
    if business.contact_email:
        lines.append(f"Contact Email: {business.contact_email}")
    if business.contact_phone:
        lines.append(f"Contact Phone: {business.contact_phone}")

    content = "\n".join(lines)
    business_id = getattr(business, "business_id", None) or "business"
    metadata = create_document_metadata(
        business_id=business_id,
        source_type="business",
        source_id=business_id,
        business_name=business.name,
    )
    return Document(page_content=content, metadata=metadata)


def build_product_document(product: Union[Product, ProductCreate]) -> Document:
    """Build a normalized atomic LangChain Document for a single product.

    Products are kept atomic as a single document without arbitrary splitting
    to maintain context integrity for price, sizes, colors, and availability.
    """
    lines: List[str] = [
        f"Product: {product.name}",
    ]
    if product.category:
        lines.append(f"Category: {product.category}")

    if product.price is not None:
        currency = product.currency or "USD"
        lines.append(f"Price: {currency} {product.price:.2f}")

    if product.sizes:
        lines.append(f"Sizes: {', '.join(product.sizes)}")

    if product.colors:
        lines.append(f"Colors: {', '.join(product.colors)}")

    if product.availability:
        formatted_avail = product.availability.replace("_", " ").title()
        lines.append(f"Availability: {formatted_avail}")

    lines.append(f"Returnable: {'Yes' if product.returnable else 'No'}")

    if product.product_url:
        lines.append(f"Product URL: {product.product_url}")

    if product.description:
        lines.append(f"Description: {product.description}")

    content = "\n".join(lines)
    source_id = getattr(product, "product_id", None) or "product"
    metadata = create_document_metadata(
        business_id=product.business_id,
        source_type="product",
        source_id=source_id,
        product_name=product.name,
        category=product.category,
        price=product.price,
        availability=product.availability,
        returnable=product.returnable,
    )
    return Document(page_content=content, metadata=metadata)


def build_policy_documents(
    policy: Union[Policy, PolicyCreate],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Build normalized LangChain Document(s) for a business policy.

    Short policies remain a single document. Long policies exceeding chunk_size
    are cleanly split using RecursiveCharacterTextSplitter.
    """
    cfg = get_config()
    c_size = chunk_size if chunk_size is not None else cfg.chunk_size
    c_overlap = chunk_overlap if chunk_overlap is not None else cfg.chunk_overlap

    formatted_type = policy.policy_type.replace("_", " ").title()
    normalized_content = f"Policy Type: {formatted_type} Policy\n\nContent:\n{policy.content}"
    source_id = getattr(policy, "policy_id", None) or "policy"

    # If policy content is within chunk limit, keep as single document
    if len(normalized_content) <= c_size:
        metadata = create_document_metadata(
            business_id=policy.business_id,
            source_type="policy",
            source_id=source_id,
            policy_type=policy.policy_type,
            chunk_index=0,
            total_chunks=1,
        )
        return [Document(page_content=normalized_content, metadata=metadata)]

    # Length-aware chunking for long policies
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=c_size,
        chunk_overlap=c_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_chunks = splitter.split_text(policy.content)
    total_chunks = len(raw_chunks)

    documents: List[Document] = []
    for idx, chunk in enumerate(raw_chunks):
        chunk_content = (
            f"Policy Type: {formatted_type} Policy (Part {idx + 1}/{total_chunks})\n\n"
            f"Content:\n{chunk}"
        )
        metadata = create_document_metadata(
            business_id=policy.business_id,
            source_type="policy",
            source_id=source_id,
            policy_type=policy.policy_type,
            chunk_index=idx,
            total_chunks=total_chunks,
        )
        documents.append(Document(page_content=chunk_content, metadata=metadata))

    return documents


def build_catalog_document(
    products: Sequence[Union[Product, ProductCreate]],
    business: Optional[Union[Business, BusinessCreate]] = None,
) -> Optional[Document]:
    """Build a normalized atomic LangChain Document summarizing the business's product catalog.

    Provides a comprehensive catalog-level overview document enabling high-relevance semantic
    retrieval for broad inventory and product questions (e.g. 'What products do you sell?').
    """
    if not products:
        return None

    biz_name = business.name if business else "the store"
    lines: List[str] = [
        f"Product Catalog & Offerings: Products We Sell at {biz_name}",
        f"We sell the following products and apparel across our collections:",
    ]
    for p in products:
        cat_str = f" (Category: {p.category})" if p.category else ""
        price_str = f" (Price: {p.currency or 'USD'} {p.price:.2f})" if p.price is not None else ""
        color_str = f" (Colors: {', '.join(p.colors)})" if p.colors else ""
        lines.append(f"- {p.name}{cat_str}{price_str}{color_str}")

    content = "\n".join(lines)
    business_id = products[0].business_id if products else (getattr(business, "business_id", None) or "business")
    metadata = create_document_metadata(
        business_id=business_id,
        source_type="product",
        source_id=f"{business_id}_catalog",
        product_name="Product Catalog",
    )
    return Document(page_content=content, metadata=metadata)


def build_faq_document(faq: Union[FAQ, FAQCreate]) -> Document:
    """Build a normalized atomic LangChain Document for an FAQ entry."""
    content = f"Question:\n{faq.question}\n\nAnswer:\n{faq.answer}"
    source_id = getattr(faq, "faq_id", None) or "faq"
    metadata = create_document_metadata(
        business_id=faq.business_id,
        source_type="faq",
        source_id=source_id,
    )
    return Document(page_content=content, metadata=metadata)


def build_all_documents(
    business: Optional[Business],
    products: List[Product],
    policies: List[Policy],
    faqs: List[FAQ],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Build and collect all normalized LangChain Documents for a business."""
    documents: List[Document] = []

    if business:
        documents.append(build_business_document(business))

    if products:
        cat_doc = build_catalog_document(products, business=business)
        if cat_doc:
            documents.append(cat_doc)

    for prod in products:
        documents.append(build_product_document(prod))

    for pol in policies:
        documents.extend(
            build_policy_documents(pol, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        )

    for faq in faqs:
        documents.append(build_faq_document(faq))

    return documents

