from langchain_core.prompts import PromptTemplate
from fastapi import HTTPException
from app.dependencies.system_propmt_templete import system_prompt_template
# Response Generation Service: Assembles prompt template with context chunks and calls the LLM.

def chat_response(retrieved_docs,prompt:str,llm):
    
        if retrieved_docs:
                formatted_context = "\n\n---\n\n".join(
                    [
                        f"[Doc {doc['rank']}] (Score: {doc.get('rerank_score', doc['similarity_score']):.3f})\n{doc['content']}"
                        for doc in retrieved_docs
                    ]
                )
        else:
            formatted_context = "No relevant context found in uploaded documents."
    
    
    
    # Formats the grounded prompt template with retrieved knowledge context and invokes the Groq LLM


        


        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=system_prompt_template
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
