from openai import OpenAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


CHROMA_PATH = "/app/chromadb"
COLLECTION_NAME = "mindcare_knowledge"


client = OpenAI()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


vector_db = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings,
)


def ask_mindcare(question):
    docs = vector_db.similarity_search(
        question,
        k=3
    )

    if not docs:
        return (
            "I couldn't find that information in the "
            "MindCare clinic knowledge base."
        )

    context = "\n\n".join(
        doc.page_content
        for doc in docs
    )

    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You are the MindCare clinic information assistant.

Answer only using the clinic information provided below.

Do not diagnose medical conditions.
Do not prescribe medication.
Do not provide treatment recommendations.

If the answer is not contained in the context, say that the
information is not available in the MindCare clinic knowledge base.

Clinic information:
{context}

User question:
{question}
"""
    )

    return response.output_text.strip()
