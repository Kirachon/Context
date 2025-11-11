"""Conversation Memory: Store and retrieve conversation history with semantic search.

Epic 5: Conversation Memory
- PostgreSQL storage for conversation data
- Qdrant vector indexing for semantic search
- CRUD operations with session management
- Similar conversation retrieval
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sentence_transformers import SentenceTransformer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.memory.database import get_db_manager
from src.memory.models import Conversation
from src.vector_db.qdrant_client import get_client as get_qdrant_client


class ConversationStore:
    """Store and retrieve conversations with semantic search capabilities."""

    COLLECTION_NAME = "conversations"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    VECTOR_SIZE = 384

    def __init__(self):
        """Initialize conversation store with database and vector DB clients."""
        self.db_manager = get_db_manager()
        self.qdrant_client = get_qdrant_client()
        self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL)

        # Ensure Qdrant collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure Qdrant collection for conversations exists."""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                from qdrant_client.models import Distance, VectorParams

                self.qdrant_client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Warning: Could not create Qdrant collection: {e}")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()

    def store_conversation(
        self,
        user_id: str,
        prompt: str,
        enhanced_prompt: Optional[str] = None,
        response: Optional[str] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None,
        token_count: Optional[int] = None,
        latency_ms: Optional[int] = None,
        context_sources: Optional[Dict] = None,
    ) -> UUID:
        """Store a conversation in PostgreSQL and index in Qdrant.

        Args:
            user_id: User identifier
            prompt: Original user prompt
            enhanced_prompt: Enhanced prompt with context
            response: AI response
            intent: Classified intent (fix, explain, implement, etc.)
            entities: Extracted entities from prompt
            token_count: Number of tokens in enhanced prompt
            latency_ms: Time taken to enhance prompt (ms)
            context_sources: Sources used for context gathering

        Returns:
            UUID of the created conversation
        """
        with self.db_manager.get_session() as session:
            # Create conversation record
            conversation = Conversation(
                id=uuid4(),
                user_id=user_id,
                timestamp=datetime.utcnow(),
                prompt=prompt,
                enhanced_prompt=enhanced_prompt,
                response=response,
                intent=intent,
                entities=entities,
                token_count=token_count,
                latency_ms=latency_ms,
                context_sources=context_sources,
            )

            session.add(conversation)
            session.flush()  # Get the ID

            conversation_id = conversation.id

            # Generate embedding for semantic search
            # Combine prompt and response for better context
            text_for_embedding = prompt
            if response:
                text_for_embedding += " " + response[:500]  # Limit response length

            try:
                embedding = self._generate_embedding(text_for_embedding)

                # Store in Qdrant
                from qdrant_client.models import PointStruct

                self.qdrant_client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=str(conversation_id),
                            vector=embedding,
                            payload={
                                "user_id": user_id,
                                "prompt": prompt,
                                "intent": intent,
                                "timestamp": conversation.timestamp.isoformat(),
                            }
                        )
                    ]
                )
            except Exception as e:
                print(f"Warning: Could not index conversation in Qdrant: {e}")

            session.commit()
            return conversation_id

    def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Retrieve a conversation by ID.

        Args:
            conversation_id: UUID of the conversation

        Returns:
            Conversation object or None if not found
        """
        with self.db_manager.get_session() as session:
            return session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

    def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations for a specific user.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of Conversation objects
        """
        with self.db_manager.get_session() as session:
            return session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(
                desc(Conversation.timestamp)
            ).limit(limit).offset(offset).all()

    def get_similar_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
        intent_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Find similar conversations using semantic search.

        Args:
            query: Search query
            user_id: Optional user ID to filter results
            limit: Maximum number of results
            intent_filter: Optional intent type to filter by

        Returns:
            List of dicts with conversation data and similarity scores
        """
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)

            # Build Qdrant filter
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_conditions = []
            if user_id:
                filter_conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                )
            if intent_filter:
                filter_conditions.append(
                    FieldCondition(key="intent", match=MatchValue(value=intent_filter))
                )

            search_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
            )

            # Fetch full conversation data from PostgreSQL
            results = []
            with self.db_manager.get_session() as session:
                for hit in search_results:
                    conversation_id = UUID(hit.id)
                    conversation = session.query(Conversation).filter(
                        Conversation.id == conversation_id
                    ).first()

                    if conversation:
                        results.append({
                            "conversation": conversation,
                            "similarity_score": hit.score,
                            "payload": hit.payload,
                        })

            return results

        except Exception as e:
            print(f"Error searching conversations: {e}")
            # Fallback to text search in PostgreSQL
            return self._text_search_fallback(query, user_id, limit, intent_filter)

    def _text_search_fallback(
        self,
        query: str,
        user_id: Optional[str],
        limit: int,
        intent_filter: Optional[str]
    ) -> List[Dict]:
        """Fallback to PostgreSQL text search if Qdrant fails.

        Args:
            query: Search query
            user_id: Optional user ID filter
            limit: Maximum results
            intent_filter: Optional intent filter

        Returns:
            List of matching conversations
        """
        with self.db_manager.get_session() as session:
            q = session.query(Conversation)

            if user_id:
                q = q.filter(Conversation.user_id == user_id)
            if intent_filter:
                q = q.filter(Conversation.intent == intent_filter)

            # Simple text matching
            q = q.filter(
                Conversation.prompt.ilike(f"%{query}%")
            )

            conversations = q.order_by(desc(Conversation.timestamp)).limit(limit).all()

            return [
                {
                    "conversation": conv,
                    "similarity_score": 0.5,  # Arbitrary score for text match
                    "payload": {"fallback": True},
                }
                for conv in conversations
            ]

    def update_feedback(
        self,
        conversation_id: UUID,
        feedback: Dict,
        resolution: Optional[bool] = None,
        helpful_score: Optional[float] = None,
    ) -> bool:
        """Update feedback for a conversation.

        Args:
            conversation_id: UUID of the conversation
            feedback: Feedback dictionary
            resolution: Whether the conversation resolved the issue
            helpful_score: Helpfulness score (0.0-1.0)

        Returns:
            True if updated successfully, False otherwise
        """
        with self.db_manager.get_session() as session:
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                return False

            conversation.feedback = feedback
            if resolution is not None:
                conversation.resolution = resolution
            if helpful_score is not None:
                conversation.helpful_score = helpful_score

            session.commit()
            return True

    def get_statistics(self, user_id: Optional[str] = None) -> Dict:
        """Get conversation statistics.

        Args:
            user_id: Optional user ID to filter statistics

        Returns:
            Dictionary with statistics
        """
        with self.db_manager.get_session() as session:
            from sqlalchemy import func

            q = session.query(Conversation)
            if user_id:
                q = q.filter(Conversation.user_id == user_id)

            total_conversations = q.count()

            # Intent distribution
            intent_stats = session.query(
                Conversation.intent,
                func.count(Conversation.id)
            ).group_by(Conversation.intent).all()

            # Average metrics
            avg_latency = q.with_entities(
                func.avg(Conversation.latency_ms)
            ).scalar()

            avg_tokens = q.with_entities(
                func.avg(Conversation.token_count)
            ).scalar()

            # Resolution rate
            resolved = q.filter(Conversation.resolution == True).count()
            resolution_rate = resolved / total_conversations if total_conversations > 0 else 0

            return {
                "total_conversations": total_conversations,
                "intent_distribution": dict(intent_stats),
                "avg_latency_ms": float(avg_latency) if avg_latency else None,
                "avg_token_count": float(avg_tokens) if avg_tokens else None,
                "resolution_rate": resolution_rate,
                "resolved_count": resolved,
            }

    def delete_old_conversations(self, days: int = 90) -> int:
        """Delete conversations older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of conversations deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.db_manager.get_session() as session:
            # Get IDs to delete from Qdrant
            old_conversations = session.query(Conversation.id).filter(
                Conversation.timestamp < cutoff_date
            ).all()

            conversation_ids = [str(conv.id) for conv in old_conversations]

            # Delete from Qdrant
            try:
                if conversation_ids:
                    from qdrant_client.models import PointIdsList

                    self.qdrant_client.delete(
                        collection_name=self.COLLECTION_NAME,
                        points_selector=PointIdsList(points=conversation_ids)
                    )
            except Exception as e:
                print(f"Warning: Could not delete from Qdrant: {e}")

            # Delete from PostgreSQL
            deleted_count = session.query(Conversation).filter(
                Conversation.timestamp < cutoff_date
            ).delete()

            session.commit()
            return deleted_count
