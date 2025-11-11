"""Solution Memory: Store problem-solution pairs with clustering.

Epic 7: Solution Memory
- Store successful problem-solution pairs
- Cluster similar problems for reuse
- Track success metrics
- Retrieve similar solutions by semantic search
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sqlalchemy import desc
import numpy as np

from src.memory.database import get_db_manager
from src.memory.models import Solution


class SolutionStore:
    """Store and retrieve problem-solution pairs with clustering."""

    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(self):
        """Initialize solution store."""
        self.db_manager = get_db_manager()
        self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL)

    def store_solution(
        self,
        problem_description: str,
        solution_code: Optional[str] = None,
        solution_description: Optional[str] = None,
        problem_type: Optional[str] = None,
        error_message: Optional[str] = None,
        files_affected: Optional[List[str]] = None,
        success_rate: float = 0.0,
        resolution_time_sec: Optional[int] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> UUID:
        """Store a problem-solution pair.

        Args:
            problem_description: Description of the problem
            solution_code: Solution code
            solution_description: Description of the solution
            problem_type: Type of problem (bug, feature, refactor, etc.)
            error_message: Associated error message
            files_affected: List of files modified
            success_rate: Success rate (0.0-1.0)
            resolution_time_sec: Time to resolve (seconds)
            user_id: User who created the solution
            project_id: Project identifier

        Returns:
            UUID of the created solution
        """
        with self.db_manager.get_session() as session:
            solution = Solution(
                id=uuid4(),
                problem_description=problem_description,
                problem_type=problem_type,
                error_message=error_message,
                solution_code=solution_code,
                solution_description=solution_description,
                files_affected={"files": files_affected} if files_affected else None,
                success_rate=success_rate,
                usage_count=1,
                avg_resolution_time_sec=resolution_time_sec,
                user_id=user_id,
                project_id=project_id,
            )

            session.add(solution)
            session.commit()

            # Trigger clustering update
            self._update_clustering(session, solution)

            return solution.id

    def get_solution(self, solution_id: UUID) -> Optional[Solution]:
        """Retrieve a solution by ID.

        Args:
            solution_id: UUID of the solution

        Returns:
            Solution object or None
        """
        with self.db_manager.get_session() as session:
            return session.query(Solution).filter(
                Solution.id == solution_id
            ).first()

    def get_solutions(
        self,
        problem_type: Optional[str] = None,
        project_id: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50,
    ) -> List[Solution]:
        """Get solutions with optional filtering.

        Args:
            problem_type: Optional problem type filter
            project_id: Optional project filter
            min_success_rate: Minimum success rate filter
            limit: Maximum number of solutions

        Returns:
            List of Solution objects
        """
        with self.db_manager.get_session() as session:
            q = session.query(Solution)

            if problem_type:
                q = q.filter(Solution.problem_type == problem_type)
            if project_id:
                q = q.filter(Solution.project_id == project_id)
            if min_success_rate > 0:
                q = q.filter(Solution.success_rate >= min_success_rate)

            return q.order_by(desc(Solution.success_rate)).limit(limit).all()

    def get_similar_solutions(
        self,
        problem: str,
        project_id: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict]:
        """Find similar solutions using semantic similarity.

        Args:
            problem: Problem description
            project_id: Optional project filter
            limit: Maximum number of solutions

        Returns:
            List of dicts with solution data and similarity scores
        """
        # Generate embedding for the problem
        problem_embedding = self.embedding_model.encode(problem)

        # Get all solutions (potentially filtered)
        with self.db_manager.get_session() as session:
            q = session.query(Solution)
            if project_id:
                q = q.filter(Solution.project_id == project_id)

            solutions = q.all()

            if not solutions:
                return []

            # Compute similarity scores
            similarities = []
            for solution in solutions:
                # Generate embedding for stored problem
                stored_embedding = self.embedding_model.encode(solution.problem_description)

                # Compute cosine similarity
                similarity = np.dot(problem_embedding, stored_embedding) / (
                    np.linalg.norm(problem_embedding) * np.linalg.norm(stored_embedding)
                )

                similarities.append({
                    "solution": solution,
                    "similarity_score": float(similarity),
                })

            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similarities[:limit]

    def update_solution_metrics(
        self,
        solution_id: UUID,
        success: bool,
        resolution_time_sec: Optional[int] = None,
    ) -> bool:
        """Update solution success metrics.

        Args:
            solution_id: UUID of the solution
            success: Whether the solution was successful
            resolution_time_sec: Time taken to resolve

        Returns:
            True if updated successfully
        """
        with self.db_manager.get_session() as session:
            solution = session.query(Solution).filter(
                Solution.id == solution_id
            ).first()

            if not solution:
                return False

            # Update usage count
            solution.usage_count += 1

            # Update success rate (moving average)
            current_total = solution.usage_count - 1
            current_successes = solution.success_rate * current_total
            new_successes = current_successes + (1 if success else 0)
            solution.success_rate = new_successes / solution.usage_count

            # Update average resolution time
            if resolution_time_sec is not None:
                if solution.avg_resolution_time_sec is None:
                    solution.avg_resolution_time_sec = resolution_time_sec
                else:
                    # Moving average
                    solution.avg_resolution_time_sec = int(
                        (solution.avg_resolution_time_sec * current_total + resolution_time_sec)
                        / solution.usage_count
                    )

            session.commit()
            return True

    def _update_clustering(self, session, new_solution: Solution):
        """Update solution clustering when a new solution is added.

        Uses DBSCAN to cluster similar problems together.

        Args:
            session: Database session
            new_solution: Newly added solution
        """
        # Get all solutions from the same project
        project_id = new_solution.project_id
        solutions = session.query(Solution).filter(
            Solution.project_id == project_id
        ).all()

        if len(solutions) < 3:
            # Need at least 3 solutions to cluster
            return

        # Generate embeddings for all problems
        descriptions = [s.problem_description for s in solutions]
        embeddings = self.embedding_model.encode(descriptions)

        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine')
        cluster_labels = clustering.fit_predict(embeddings)

        # Update cluster IDs for each solution
        for solution, cluster_label in zip(solutions, cluster_labels):
            if cluster_label != -1:  # -1 means noise/outlier
                solution.cluster_id = f"{project_id}_cluster_{cluster_label}"

                # Find similar problems in the same cluster
                similar_ids = [
                    str(s.id) for s, label in zip(solutions, cluster_labels)
                    if label == cluster_label and s.id != solution.id
                ]

                solution.similar_problems = {"similar_solution_ids": similar_ids}

        session.commit()

    def recluster_solutions(self, project_id: Optional[str] = None) -> Dict:
        """Recluster all solutions.

        Args:
            project_id: Optional project filter

        Returns:
            Clustering statistics
        """
        with self.db_manager.get_session() as session:
            q = session.query(Solution)
            if project_id:
                q = q.filter(Solution.project_id == project_id)

            solutions = q.all()

            if len(solutions) < 3:
                return {"clusters": 0, "solutions": len(solutions)}

            # Generate embeddings
            descriptions = [s.problem_description for s in solutions]
            embeddings = self.embedding_model.encode(descriptions)

            # Perform clustering
            clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine')
            cluster_labels = clustering.fit_predict(embeddings)

            # Count clusters
            unique_clusters = set(label for label in cluster_labels if label != -1)

            # Update all solutions
            for solution, cluster_label in zip(solutions, cluster_labels):
                if cluster_label != -1:
                    proj_id = solution.project_id or "global"
                    solution.cluster_id = f"{proj_id}_cluster_{cluster_label}"

                    # Find similar problems
                    similar_ids = [
                        str(s.id) for s, label in zip(solutions, cluster_labels)
                        if label == cluster_label and s.id != solution.id
                    ]

                    solution.similar_problems = {"similar_solution_ids": similar_ids}
                else:
                    solution.cluster_id = None
                    solution.similar_problems = None

            session.commit()

            return {
                "clusters": len(unique_clusters),
                "solutions": len(solutions),
                "outliers": sum(1 for label in cluster_labels if label == -1),
            }

    def get_solution_statistics(self, project_id: Optional[str] = None) -> Dict:
        """Get solution statistics.

        Args:
            project_id: Optional project filter

        Returns:
            Dictionary with statistics
        """
        with self.db_manager.get_session() as session:
            from sqlalchemy import func

            q = session.query(Solution)
            if project_id:
                q = q.filter(Solution.project_id == project_id)

            total_solutions = q.count()

            # Average success rate
            avg_success_rate = q.with_entities(
                func.avg(Solution.success_rate)
            ).scalar()

            # Problem type distribution
            type_stats = session.query(
                Solution.problem_type,
                func.count(Solution.id)
            ).group_by(Solution.problem_type)

            if project_id:
                type_stats = type_stats.filter(Solution.project_id == project_id)

            type_distribution = dict(type_stats.all())

            # Cluster statistics
            cluster_count = session.query(Solution.cluster_id).distinct().count()

            # Most successful solutions
            top_solutions = q.filter(
                Solution.success_rate > 0.5
            ).order_by(desc(Solution.success_rate)).limit(10).all()

            return {
                "total_solutions": total_solutions,
                "avg_success_rate": float(avg_success_rate) if avg_success_rate else 0.0,
                "problem_type_distribution": type_distribution,
                "cluster_count": cluster_count,
                "top_solutions": [
                    {
                        "id": str(s.id),
                        "problem_type": s.problem_type,
                        "success_rate": s.success_rate,
                        "usage_count": s.usage_count,
                    }
                    for s in top_solutions
                ],
            }

    def delete_low_performing_solutions(
        self,
        max_success_rate: float = 0.3,
        min_usage_count: int = 5,
    ) -> int:
        """Delete solutions with low success rate.

        Args:
            max_success_rate: Maximum success rate to keep (delete below this)
            min_usage_count: Minimum usage count required before considering deletion

        Returns:
            Number of solutions deleted
        """
        with self.db_manager.get_session() as session:
            deleted_count = session.query(Solution).filter(
                Solution.success_rate < max_success_rate,
                Solution.usage_count >= min_usage_count,
            ).delete()

            session.commit()
            return deleted_count
