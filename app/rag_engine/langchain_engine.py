"""LangChain-powered regulatory answer generation."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


REGULATORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a regulatory intelligence assistant.

Answer questions using ONLY the supplied regulatory evidence.

Rules:
1. Do not invent regulatory requirements.
2. Cite each factual regulatory claim using [Source N].
3. Every regulatory bullet must have its own citation.
4. Preserve deadlines, conditions, and exceptions.
5. If evidence is insufficient, explain what is missing.
6. Do not make unsupported claims that no other obligations exist.
7. Do not present your answer as legal advice.

Retrieved regulatory evidence:

{context}
""",
        ),
        (
            "human",
            "{question}",
        ),
    ]
)


def generate_regulatory_answer(
    question: str,
    context: str,
    model_name: str = "qwen2.5:7b",
) -> str:
    """
    Generate a regulatory answer using LangChain and local Ollama.
    """

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not context.strip():
        raise ValueError("Regulatory evidence cannot be empty.")

    llm = ChatOllama(
        model=model_name,
        temperature=0,
    )

    chain = REGULATORY_PROMPT | llm

    response = chain.invoke(
        {
            "question": question,
            "context": context,
        }
    )

    return response.content.strip()