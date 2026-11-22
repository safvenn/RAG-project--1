
# Response Generation Service: Assembles prompt template with context chunks and calls the LLM.

def chat_response(formatted_context,prompt:str):
    # Formats the grounded prompt template with retrieved knowledge context and invokes the Groq LLM


        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful AI assistant. Use the following context to answer the question accurately and concisely.

    Context:
    {context}

    Question: {question}

    Answer: Provide a clear and informative answer based on the context above. If the context doesn't contain enough information to answer the question, say so. Also Provide Sources Where it from in the bottom."""
        )

        formatted_prompt = prompt_template.format(context=formatted_context, question=prompt)

        try:
            response = llm.invoke([formatted_prompt])
            return {
                "data": {
                    "You": prompt,
                    "Ai": response.content,
                    "sources": [
                        {
                            "id": d["id"],
                            "rank": d["rank"],
                            "score": round(d.get("rerank_score", d["similarity_score"]), 4),
                            "metadata": d["metadata"]
                        }
                        for d in retrieved_docs
                    ]
                }
            }

        except Exception as e:
            raise HTTPException(detail=f"Error generating response: {str(e)}", status_code=500)
