#!/usr/bin/env python3

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from pinecone import Pinecone
from groq import Groq
import time
from sentence_transformers import SentenceTransformer

# Fix tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables
load_dotenv()

class RAGSystem:
    def __init__(self):
        """Initialize RAG system with Pinecone and Groq"""
        
        # Initialize embedding model
        print("🎆 Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings
        print("✅ Embedding model loaded")
        
        # Initialize Pinecone
        self.pc_api_key = os.getenv("PINECONE_API_KEY")
        if not self.pc_api_key:
            raise ValueError("Please set PINECONE_API_KEY in .env file")
        
        self.pc = Pinecone(api_key=self.pc_api_key)
        
        # Initialize or get index
        self.index_name = "kmrl-documents"
        self.setup_pinecone_index()
        
        # Initialize Groq
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("Please set GROQ_API_KEY in .env file")
        
        self.groq_client = Groq(api_key=self.groq_api_key)
        
    def setup_pinecone_index(self):
        """Create or connect to Pinecone index"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                print(f"🔨 Creating new Pinecone index: {self.index_name}")
                
                # Create a new serverless index
                from pinecone import ServerlessSpec
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=384,  # Using a standard embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                
                # Wait for index to be ready
                import time
                while not self.pc.describe_index(self.index_name).status['ready']:
                    time.sleep(1)
                print(f"✅ Index {self.index_name} created successfully")
            else:
                print(f"✅ Connected to existing index: {self.index_name}")
            
            # Get index
            self.index = self.pc.Index(self.index_name)
            
        except Exception as e:
            print(f"❌ Error setting up Pinecone index: {e}")
            # If index creation fails, try to connect to existing
            try:
                self.index = self.pc.Index(self.index_name)
                print(f"✅ Connected to existing index despite error")
            except:
                raise e

    def chunk_document(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split document into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks

    def upsert_document(self, filename: str, document_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Upsert document chunks to Pinecone index"""
        try:
            # Extract text from document
            text_parts = []
            for element in document_data:
                text = element.get('text', '').strip()
                if text:
                    text_parts.append(text)
            
            full_text = ' '.join(text_parts)
            
            if not full_text:
                return {'success': False, 'error': 'No text content found in document'}
            
            # Create chunks
            chunks = self.chunk_document(full_text)
            
            # Prepare records for upsert
            records = []
            for i, chunk in enumerate(chunks):
                # Create unique ID for each chunk
                chunk_id = hashlib.md5(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest()
                
                record = {
                    "_id": chunk_id,
                    "text": chunk,  # This will be embedded by Pinecone
                    "document_name": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # Add metadata if provided
                if metadata:
                    record.update({
                        "document_title": metadata.get('document_title', filename),
                        "categories": ', '.join(metadata.get('document_categories', [])),
                        "from_whom": metadata.get('from_whom', ''),
                        "to_whom": metadata.get('to_whom', ''),
                        "date": metadata.get('date', ''),
                        "job_to_do": metadata.get('job_to_do', '')
                    })
                
                records.append(record)
            
            # Generate real embeddings using sentence-transformers
            print(f"🧬 Generating embeddings for {len(records)} chunks...")
            
            # Upsert to Pinecone
            namespace = metadata.get('document_categories', ['general'])[0].lower() if metadata else 'general'
            
            vectors_to_upsert = []
            for record in records:
                # Generate embedding for the chunk text
                embedding = self.embedder.encode(record['text']).tolist()
                
                vectors_to_upsert.append({
                    "id": record["_id"],
                    "values": embedding,
                    "metadata": record
                })
            
            # Upsert in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
            
            print(f"✅ Upserted {len(records)} chunks from {filename} to namespace '{namespace}'")
            
            return {
                'success': True,
                'chunks_created': len(chunks),
                'namespace': namespace,
                'document': filename
            }
            
        except Exception as e:
            print(f"❌ Error upserting document: {e}")
            return {'success': False, 'error': str(e)}

    def search_documents(self, query: str, role: str = "Admin", top_k: int = 5, namespace: str = None) -> List[Dict]:
        """Search for relevant document chunks"""
        try:
            # Generate real query embedding
            query_embedding = self.embedder.encode(query).tolist()
            
            # Search all namespaces to find documents
            all_results = []
            
            # Get actual namespaces from index stats
            try:
                stats = self.index.describe_index_stats()
                actual_namespaces = list(stats.get('namespaces', {}).keys())
                print(f"📊 Available namespaces: {actual_namespaces}")
                
                # Search in actual namespaces plus some common ones
                namespaces_to_search = actual_namespaces + ["general", "safety", "hr", "engineering", "finance"]
                # Remove duplicates
                namespaces_to_search = list(set(namespaces_to_search))
            except:
                # Fallback to default namespaces
                namespaces_to_search = ["general", "safety", "hr", "engineering", "finance"]
                
            if namespace:
                namespaces_to_search = [namespace] + namespaces_to_search
            
            print(f"🔍 Searching for: '{query}' in namespaces: {namespaces_to_search}")
            
            for ns in namespaces_to_search:
                try:
                    # Query Pinecone
                    results = self.index.query(
                        vector=query_embedding,
                        top_k=top_k,
                        include_metadata=True,
                        namespace=ns
                    )
                    
                    print(f"📊 Found {len(results.get('matches', []))} matches in namespace '{ns}'")
                    
                    # Format results
                    for match in results.get('matches', []):
                        all_results.append({
                            'text': match.get('metadata', {}).get('text', ''),
                            'document_name': match.get('metadata', {}).get('document_name', ''),
                            'chunk_index': match.get('metadata', {}).get('chunk_index', 0),
                            'score': match.get('score', 0),
                            'namespace': ns
                        })
                except Exception as e:
                    print(f"⚠️ Error searching namespace '{ns}': {e}")
                    continue
            
            # Sort by score and return top results
            all_results.sort(key=lambda x: x['score'], reverse=True)
            final_results = all_results[:top_k]
            
            print(f"📋 Final results: {len(final_results)} documents found")
            for r in final_results:
                print(f"  - {r['document_name']} (score: {r['score']:.3f})")
            
            return final_results
            
        except Exception as e:
            print(f"❌ Error searching documents: {e}")
            return []

    def chat_with_documents(self, query: str, role: str = "Admin", conversation_history: List = None) -> Dict[str, Any]:
        """Chat with documents using RAG"""
        try:
            print(f"💬 Starting chat for query: '{query}' (Role: {role})")
            
            # Search for relevant chunks
            relevant_chunks = self.search_documents(query, role)
            
            print(f"📄 Retrieved {len(relevant_chunks)} relevant chunks")
            
            # Build context from relevant chunks
            context = ""
            sources = []
            
            for chunk in relevant_chunks:
                chunk_text = chunk.get('text', '').strip()
                if chunk_text:
                    context += f"\n{chunk_text}\n"
                    sources.append({
                        'document': chunk.get('document_name', ''),
                        'chunk_index': chunk.get('chunk_index', 0)
                    })
            
            print(f"📝 Context length: {len(context)} chars, Sources: {len(sources)}")
            if context:
                print(f"🔍 Context preview: {context[:200]}...")
            
            # Build messages for Groq
            messages = []
            
            # Enhanced system prompt for structured responses
            system_prompt = f"""You are KMRL Assistant. Provide ONLY essential facts.

**STRICT RULES:**
• **No thinking/reasoning** - Start directly with facts
• **Maximum 50 words total**
• **Bullet points only** for multiple items
• **Format**: • [Topic]: [Deadline/Action] ([Document])

**Information:**
{context if context else "No documents found."}

**Output ONLY facts - no explanations, no thinking, no context."""
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                    messages.append(msg)
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Get streaming response from Groq
            completion = self.groq_client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=messages,
                temperature=0.3,
                max_completion_tokens=200,
                top_p=0.95,
                reasoning_effort="default",
                stream=True,
                stop=None
            )
            
            # Collect streaming response
            response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    response += chunk.choices[0].delta.content
            
            return {
                'success': True,
                'response': response,
                'sources': sources,
                'context_used': bool(context)
            }
            
        except Exception as e:
            print(f"❌ Error in chat: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "I apologize, but I encountered an error processing your request."
            }

    def chat_with_documents_stream(self, query: str, role: str = "Admin", conversation_history: List = None):
        """Chat with documents using RAG with streaming response"""
        try:
            print(f"💬 Starting streaming chat for query: '{query}' (Role: {role})")
            
            # Search for relevant chunks
            relevant_chunks = self.search_documents(query, role)
            
            print(f"📄 Retrieved {len(relevant_chunks)} relevant chunks")
            
            # Build context from relevant chunks
            context = ""
            sources = []
            
            for chunk in relevant_chunks:
                chunk_text = chunk.get('text', '').strip()
                if chunk_text:
                    context += f"\n{chunk_text}\n"
                    sources.append({
                        'document': chunk.get('document_name', ''),
                        'chunk_index': chunk.get('chunk_index', 0)
                    })
            
            # Build messages for Groq
            messages = []
            
            # Enhanced system prompt
            system_prompt = f"""You are KMRL Assistant. Provide ONLY essential facts.

**STRICT RULES:**
• **No thinking/reasoning** - Start directly with facts
• **Maximum 50 words total**
• **Bullet points only** for multiple items
• **Format**: • [Topic]: [Deadline/Action] ([Document])

**Information:**
{context if context else "No documents found."}

**Output ONLY facts - no explanations, no thinking, no context."""
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-6:]:
                    messages.append(msg)
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Get streaming response from Groq
            completion = self.groq_client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=messages,
                temperature=0.3,
                max_completion_tokens=200,
                top_p=0.95,
                reasoning_effort="default",
                stream=True,
                stop=None
            )
            
            # Return streaming generator with metadata
            def stream_generator():
                yield f"data: {json.dumps({'type': 'start', 'sources': sources, 'context_used': bool(context)})}\n\n"
                
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        chunk_data = {
                            'type': 'chunk',
                            'content': chunk.choices[0].delta.content
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
            return stream_generator()
            
        except Exception as e:
            print(f"❌ Error in streaming chat: {e}")
            def error_generator():
                error_data = {'type': 'error', 'error': str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
            return error_generator()

    def index_all_processed_documents(self, output_dir: str = "output_documenty", metadata_dir: str = "metadata") -> Dict[str, Any]:
        """Index all processed documents into Pinecone"""
        output_path = Path(output_dir)
        metadata_path = Path(metadata_dir)
        
        if not output_path.exists():
            return {'success': False, 'error': f'Output directory {output_dir} not found'}
        
        results = {
            'success': True,
            'indexed': [],
            'failed': [],
            'total': 0
        }
        
        json_files = list(output_path.glob("*.json"))
        results['total'] = len(json_files)
        
        for json_file in json_files:
            try:
                # Load document data
                with open(json_file, 'r', encoding='utf-8') as f:
                    document_data = json.load(f)
                
                # Try to load metadata if exists
                metadata = None
                metadata_file = metadata_path / f"{json_file.stem}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata_data = json.load(f)
                        metadata = metadata_data.get('metadata', {})
                
                # Upsert to Pinecone
                result = self.upsert_document(json_file.name, document_data, metadata)
                
                if result['success']:
                    results['indexed'].append(json_file.name)
                else:
                    results['failed'].append({'file': json_file.name, 'error': result.get('error')})
                
                # Small delay to avoid rate limits
                time.sleep(1)
                
            except Exception as e:
                results['failed'].append({'file': json_file.name, 'error': str(e)})
        
        print(f"\n📊 Indexing Complete:")
        print(f"✅ Successfully indexed: {len(results['indexed'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        
        return results

    def debug_index_stats(self) -> Dict[str, Any]:
        """Check what's actually in the Pinecone index"""
        try:
            stats = self.index.describe_index_stats()
            print(f"📊 Pinecone Index Stats:")
            print(f"  Total vectors: {stats.get('total_vector_count', 0)}")
            print(f"  Namespaces: {list(stats.get('namespaces', {}).keys())}")
            
            for ns, ns_stats in stats.get('namespaces', {}).items():
                print(f"  - {ns}: {ns_stats.get('vector_count', 0)} vectors")
            
            return stats
        except Exception as e:
            print(f"❌ Error getting index stats: {e}")
            return {}

    def _get_role_focus(self, role: str) -> str:
        """Get role-specific focus for system prompt"""
        role_focuses = {
            "Admin": "• Focus on comprehensive overviews, deadlines, and cross-departmental coordination\n• Highlight urgent actions and compliance requirements",
            "Engineer": "• Emphasize technical specifications, design changes, and safety requirements\n• Prioritize engineering standards and implementation details",
            "HR": "• Focus on personnel policies, training requirements, and compliance\n• Highlight staff-related deadlines and policy updates",
            "Safety": "• Prioritize safety protocols, hazard assessments, and emergency procedures\n• Emphasize compliance deadlines and safety training requirements",
            "Manager": "• Focus on operational impact, resource allocation, and team coordination\n• Highlight departmental responsibilities and strategic implications",
            "Operations": "• Emphasize operational procedures, service impacts, and daily operations\n• Focus on immediate operational requirements and schedule impacts",
            "Finance": "• Focus on budget implications, cost analysis, and financial compliance\n• Highlight procurement and financial deadlines",
            "Procurement": "• Emphasize supplier requirements, material specifications, and procurement deadlines\n• Focus on supply chain and vendor coordination"
        }
        
        return role_focuses.get(role, "• Provide comprehensive information relevant to metro operations\n• Focus on actionable insights and clear next steps")

# For testing
if __name__ == "__main__":
    rag = RAGSystem()
    
    # Index all documents
    result = rag.index_all_processed_documents()
    print(f"Indexing result: {result}")
    
    # Test chat
    response = rag.chat_with_documents("What safety bulletins are there?", role="Admin")
    print(f"\nChat response: {response['response']}")
