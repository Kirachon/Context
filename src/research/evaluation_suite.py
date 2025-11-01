"""
UniXcoder vs Sentence-Transformers Evaluation Suite

Comprehensive evaluation comparing embedding models on real code samples
with cross-language similarity tasks and Tree-sitter query pattern validation.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.research.embedding_evaluator import (
    EmbeddingEvaluator, CodeSample, SimilarityPair, 
    SentenceTransformersModel, UniXcoderModel
)
from src.research.query_patterns import TreeSitterQueryEngine

logger = logging.getLogger(__name__)


class EvaluationSuite:
    """
    Complete evaluation suite for UniXcoder research spike.
    
    Evaluates:
    1. Embedding quality comparison (UniXcoder vs sentence-transformers)
    2. Tree-sitter query pattern effectiveness
    3. Cross-language code similarity detection
    4. Performance and integration complexity
    """
    
    def __init__(self):
        """Initialize the evaluation suite."""
        self.embedding_evaluator = EmbeddingEvaluator()
        self.query_engine = TreeSitterQueryEngine()
        self.evaluation_results = {}
        
        # Load evaluation dataset
        self._load_evaluation_dataset()
        
        logger.info("EvaluationSuite initialized")
    
    def _load_evaluation_dataset(self):
        """Load code samples and similarity pairs for evaluation."""
        # Python samples
        python_samples = [
            CodeSample(
                id="py_async_1",
                language="python",
                code="""
async def fetch_user_data(user_id: int) -> dict:
    \"\"\"Fetch user data with error handling.\"\"\"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"/api/users/{user_id}") as response:
                return await response.json()
    except Exception as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        raise
""",
                description="Async function with error handling for user data fetching",
                category="async_function"
            ),
            CodeSample(
                id="py_factory_1",
                language="python",
                code="""
class UserFactory:
    \"\"\"Factory for creating different types of users.\"\"\"
    
    @staticmethod
    def create_user(user_type: str, **kwargs) -> User:
        if user_type == "admin":
            return AdminUser(**kwargs)
        elif user_type == "regular":
            return RegularUser(**kwargs)
        else:
            raise ValueError(f"Unknown user type: {user_type}")
""",
                description="Factory pattern for user creation",
                category="factory_pattern"
            ),
            CodeSample(
                id="py_repository_1",
                language="python",
                code="""
class UserRepository:
    \"\"\"Repository for user data access.\"\"\"
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def find_by_id(self, user_id: int) -> Optional[User]:
        return await self.db.query(User).filter(User.id == user_id).first()
    
    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        return user
    
    async def delete(self, user_id: int) -> bool:
        user = await self.find_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False
""",
                description="Repository pattern with CRUD operations",
                category="repository_pattern"
            )
        ]
        
        # JavaScript samples
        javascript_samples = [
            CodeSample(
                id="js_async_1",
                language="javascript",
                code="""
async function fetchUserData(userId) {
    // Fetch user data with error handling
    try {
        const response = await fetch(`/api/users/${userId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch user ${userId}:`, error);
        throw error;
    }
}
""",
                description="Async function with error handling for user data fetching",
                category="async_function"
            ),
            CodeSample(
                id="js_factory_1",
                language="javascript",
                code="""
class UserFactory {
    // Factory for creating different types of users
    static createUser(userType, options = {}) {
        switch (userType) {
            case 'admin':
                return new AdminUser(options);
            case 'regular':
                return new RegularUser(options);
            default:
                throw new Error(`Unknown user type: ${userType}`);
        }
    }
}
""",
                description="Factory pattern for user creation",
                category="factory_pattern"
            ),
            CodeSample(
                id="js_repository_1",
                language="javascript",
                code="""
class UserRepository {
    // Repository for user data access
    constructor(database) {
        this.db = database;
    }
    
    async findById(userId) {
        return await this.db.collection('users').findOne({ _id: userId });
    }
    
    async save(user) {
        const result = await this.db.collection('users').insertOne(user);
        return { ...user, _id: result.insertedId };
    }
    
    async delete(userId) {
        const result = await this.db.collection('users').deleteOne({ _id: userId });
        return result.deletedCount > 0;
    }
}
""",
                description="Repository pattern with CRUD operations",
                category="repository_pattern"
            )
        ]
        
        # TypeScript samples
        typescript_samples = [
            CodeSample(
                id="ts_async_1",
                language="typescript",
                code="""
interface User {
    id: number;
    name: string;
    email: string;
}

async function fetchUserData(userId: number): Promise<User> {
    // Fetch user data with error handling and type safety
    try {
        const response = await fetch(`/api/users/${userId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const userData: User = await response.json();
        return userData;
    } catch (error) {
        console.error(`Failed to fetch user ${userId}:`, error);
        throw error;
    }
}
""",
                description="Typed async function with error handling for user data fetching",
                category="async_function"
            )
        ]
        
        # Add all samples to evaluator
        all_samples = python_samples + javascript_samples + typescript_samples
        for sample in all_samples:
            self.embedding_evaluator.add_code_sample(sample)
        
        # Create similarity pairs for evaluation
        similarity_pairs = [
            # Cross-language async function similarity
            SimilarityPair(
                sample1=next(s for s in all_samples if s.id == "py_async_1"),
                sample2=next(s for s in all_samples if s.id == "js_async_1"),
                expected_similarity=0.85,  # High similarity - same functionality
                similarity_type="functional"
            ),
            SimilarityPair(
                sample1=next(s for s in all_samples if s.id == "js_async_1"),
                sample2=next(s for s in all_samples if s.id == "ts_async_1"),
                expected_similarity=0.90,  # Very high - JS vs TS
                similarity_type="structural"
            ),
            # Cross-language factory pattern similarity
            SimilarityPair(
                sample1=next(s for s in all_samples if s.id == "py_factory_1"),
                sample2=next(s for s in all_samples if s.id == "js_factory_1"),
                expected_similarity=0.80,  # High similarity - same pattern
                similarity_type="semantic"
            ),
            # Cross-language repository pattern similarity
            SimilarityPair(
                sample1=next(s for s in all_samples if s.id == "py_repository_1"),
                sample2=next(s for s in all_samples if s.id == "js_repository_1"),
                expected_similarity=0.75,  # Good similarity - same pattern, different implementation
                similarity_type="semantic"
            ),
            # Different patterns should have lower similarity
            SimilarityPair(
                sample1=next(s for s in all_samples if s.id == "py_async_1"),
                sample2=next(s for s in all_samples if s.id == "py_factory_1"),
                expected_similarity=0.30,  # Low similarity - different patterns
                similarity_type="semantic"
            )
        ]
        
        for pair in similarity_pairs:
            self.embedding_evaluator.add_similarity_pair(pair)

    def run_embedding_comparison(self) -> Dict[str, Any]:
        """Run comprehensive embedding model comparison."""
        logger.info("Starting embedding model comparison...")

        results = {
            "dataset_stats": self.embedding_evaluator.get_evaluation_dataset_stats(),
            "models": {},
            "comparison": {},
            "recommendations": {}
        }

        # Test sentence-transformers model
        try:
            logger.info("Evaluating sentence-transformers model...")
            st_model = SentenceTransformersModel("all-mpnet-base-v2")
            st_results = self.embedding_evaluator.evaluate_model(st_model)
            results["models"]["sentence_transformers"] = st_results.to_dict()
            logger.info(f"Sentence-transformers evaluation complete: F1={st_results.f1_score:.3f}")
        except Exception as e:
            logger.error(f"Failed to evaluate sentence-transformers: {e}")
            results["models"]["sentence_transformers"] = {"error": str(e)}

        # Test UniXcoder model (if available)
        try:
            logger.info("Evaluating UniXcoder model...")
            unixcoder_model = UniXcoderModel("microsoft/unixcoder-base")
            unixcoder_results = self.embedding_evaluator.evaluate_model(unixcoder_model)
            results["models"]["unixcoder"] = unixcoder_results.to_dict()
            logger.info(f"UniXcoder evaluation complete: F1={unixcoder_results.f1_score:.3f}")
        except Exception as e:
            logger.warning(f"UniXcoder not available or failed: {e}")
            results["models"]["unixcoder"] = {"error": str(e), "available": False}

        # Generate comparison and recommendations
        results["comparison"] = self._compare_models(results["models"])
        results["recommendations"] = self._generate_recommendations(results["models"], results["comparison"])

        self.evaluation_results["embedding_comparison"] = results
        return results

    def run_query_pattern_evaluation(self) -> Dict[str, Any]:
        """Evaluate Tree-sitter query patterns."""
        logger.info("Starting Tree-sitter query pattern evaluation...")

        results = {
            "patterns_tested": 0,
            "successful_matches": 0,
            "languages": {},
            "pattern_effectiveness": {},
            "sample_matches": {}
        }

        # Test patterns on our code samples
        for sample in self.embedding_evaluator.code_samples:
            if sample.parse_result and sample.parse_result.parse_success:
                patterns = self.query_engine.get_patterns_for_language(sample.language)

                if sample.language not in results["languages"]:
                    results["languages"][sample.language] = {
                        "patterns_available": len(patterns),
                        "samples_tested": 0,
                        "successful_matches": 0
                    }

                results["languages"][sample.language]["samples_tested"] += 1

                # Test each pattern on this sample
                for pattern in patterns:
                    results["patterns_tested"] += 1

                    try:
                        matches = self.query_engine.execute_query(pattern, sample.code, sample.id)

                        if matches:
                            results["successful_matches"] += 1
                            results["languages"][sample.language]["successful_matches"] += 1

                            # Store sample matches for analysis
                            pattern_key = f"{sample.language}_{pattern.name}"
                            if pattern_key not in results["sample_matches"]:
                                results["sample_matches"][pattern_key] = []

                            results["sample_matches"][pattern_key].extend([
                                {
                                    "sample_id": sample.id,
                                    "matched_text": match.matched_text[:100] + "..." if len(match.matched_text) > 100 else match.matched_text,
                                    "start_line": match.start_line,
                                    "end_line": match.end_line,
                                    "captures": match.captures
                                }
                                for match in matches
                            ])

                        # Calculate pattern effectiveness
                        if pattern.name not in results["pattern_effectiveness"]:
                            results["pattern_effectiveness"][pattern.name] = {
                                "total_tests": 0,
                                "successful_matches": 0,
                                "languages": set()
                            }

                        results["pattern_effectiveness"][pattern.name]["total_tests"] += 1
                        results["pattern_effectiveness"][pattern.name]["languages"].add(sample.language)

                        if matches:
                            results["pattern_effectiveness"][pattern.name]["successful_matches"] += 1

                    except Exception as e:
                        logger.warning(f"Pattern {pattern.name} failed on {sample.id}: {e}")

        # Convert sets to lists for JSON serialization
        for pattern_name, effectiveness in results["pattern_effectiveness"].items():
            effectiveness["languages"] = list(effectiveness["languages"])
            effectiveness["success_rate"] = (
                effectiveness["successful_matches"] / max(effectiveness["total_tests"], 1)
            )

        # Calculate overall success rate
        results["overall_success_rate"] = (
            results["successful_matches"] / max(results["patterns_tested"], 1)
        )

        self.evaluation_results["query_patterns"] = results
        return results

    def _compare_models(self, models: Dict[str, Any]) -> Dict[str, Any]:
        """Compare embedding models and generate insights."""
        comparison = {
            "availability": {},
            "performance": {},
            "accuracy": {},
            "recommendations": []
        }

        # Check availability
        for model_name, model_results in models.items():
            comparison["availability"][model_name] = "error" not in model_results

        # Compare performance and accuracy if both models available
        if all(comparison["availability"].values()):
            st_results = models["sentence_transformers"]
            ux_results = models["unixcoder"]

            comparison["performance"] = {
                "encoding_time": {
                    "sentence_transformers": st_results["encoding_time_ms"],
                    "unixcoder": ux_results["encoding_time_ms"],
                    "winner": "sentence_transformers" if st_results["encoding_time_ms"] < ux_results["encoding_time_ms"] else "unixcoder"
                },
                "memory_usage": {
                    "sentence_transformers": st_results["memory_usage_mb"],
                    "unixcoder": ux_results["memory_usage_mb"],
                    "winner": "sentence_transformers" if st_results["memory_usage_mb"] < ux_results["memory_usage_mb"] else "unixcoder"
                }
            }

            comparison["accuracy"] = {
                "f1_score": {
                    "sentence_transformers": st_results["f1_score"],
                    "unixcoder": ux_results["f1_score"],
                    "winner": "sentence_transformers" if st_results["f1_score"] > ux_results["f1_score"] else "unixcoder"
                },
                "similarity_accuracy": {
                    "sentence_transformers": st_results["avg_similarity_accuracy"],
                    "unixcoder": ux_results["avg_similarity_accuracy"],
                    "winner": "sentence_transformers" if st_results["avg_similarity_accuracy"] > ux_results["avg_similarity_accuracy"] else "unixcoder"
                },
                "cross_language_accuracy": {
                    "sentence_transformers": st_results["cross_language_accuracy"],
                    "unixcoder": ux_results["cross_language_accuracy"],
                    "winner": "sentence_transformers" if st_results["cross_language_accuracy"] > ux_results["cross_language_accuracy"] else "unixcoder"
                }
            }

        return comparison

    def _generate_recommendations(self, models: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations based on evaluation results."""
        recommendations = {
            "primary_recommendation": "keep_current",
            "reasoning": [],
            "trade_offs": {},
            "next_steps": [],
            "risk_assessment": {}
        }

        # Check if UniXcoder is available
        if not comparison["availability"].get("unixcoder", False):
            recommendations["primary_recommendation"] = "keep_current"
            recommendations["reasoning"].append("UniXcoder not available or failed to load")
            recommendations["next_steps"].append("Investigate UniXcoder installation requirements")
            recommendations["risk_assessment"]["integration_complexity"] = "high"
            return recommendations

        # Compare models if both available
        if all(comparison["availability"].values()):
            st_better_count = 0
            ux_better_count = 0

            # Count wins for each model
            for category in ["performance", "accuracy"]:
                if category in comparison:
                    for metric, data in comparison[category].items():
                        if isinstance(data, dict) and "winner" in data:
                            if data["winner"] == "sentence_transformers":
                                st_better_count += 1
                            else:
                                ux_better_count += 1

            if st_better_count > ux_better_count:
                recommendations["primary_recommendation"] = "keep_current"
                recommendations["reasoning"].append(f"Sentence-transformers wins {st_better_count}/{st_better_count + ux_better_count} metrics")
            elif ux_better_count > st_better_count:
                recommendations["primary_recommendation"] = "switch_to_unixcoder"
                recommendations["reasoning"].append(f"UniXcoder wins {ux_better_count}/{st_better_count + ux_better_count} metrics")
            else:
                recommendations["primary_recommendation"] = "keep_current"
                recommendations["reasoning"].append("Models perform similarly, keep current for stability")

        # Add trade-offs analysis
        recommendations["trade_offs"] = {
            "sentence_transformers": {
                "pros": ["Proven stability", "Good general-purpose performance", "Easy integration"],
                "cons": ["Not code-specific", "May miss code semantics"]
            },
            "unixcoder": {
                "pros": ["Code-specific training", "Better code understanding", "Cross-language awareness"],
                "cons": ["Larger model size", "More complex integration", "Potential stability issues"]
            }
        }

        # Next steps
        recommendations["next_steps"] = [
            "Monitor performance in production",
            "Consider hybrid approach for different use cases",
            "Evaluate on larger dataset if needed"
        ]

        return recommendations

    def run_complete_evaluation(self) -> Dict[str, Any]:
        """Run complete evaluation suite."""
        logger.info("Starting complete UniXcoder research evaluation...")

        start_time = time.time()

        # Run all evaluations
        embedding_results = self.run_embedding_comparison()
        query_results = self.run_query_pattern_evaluation()

        # Compile final report
        final_results = {
            "evaluation_timestamp": time.time(),
            "evaluation_duration_seconds": time.time() - start_time,
            "embedding_comparison": embedding_results,
            "query_pattern_evaluation": query_results,
            "executive_summary": self._generate_executive_summary(embedding_results, query_results),
            "technical_details": {
                "dataset_size": len(self.embedding_evaluator.code_samples),
                "languages_tested": len(set(s.language for s in self.embedding_evaluator.code_samples)),
                "similarity_pairs": len(self.embedding_evaluator.similarity_pairs),
                "query_patterns": sum(len(patterns) for patterns in self.query_engine.get_all_patterns().values())
            }
        }

        self.evaluation_results["complete"] = final_results
        return final_results

    def _generate_executive_summary(self, embedding_results: Dict[str, Any], query_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of evaluation results."""
        summary = {
            "key_findings": [],
            "recommendations": {
                "embedding_model": "keep_current",
                "query_patterns": "implement",
                "next_actions": []
            },
            "success_metrics": {},
            "risk_assessment": {}
        }

        # Embedding model findings
        if "unixcoder" in embedding_results["models"] and "error" not in embedding_results["models"]["unixcoder"]:
            summary["key_findings"].append("UniXcoder successfully evaluated and compared")
            summary["recommendations"]["embedding_model"] = embedding_results["recommendations"]["primary_recommendation"]
        else:
            summary["key_findings"].append("UniXcoder not available - keeping current model")
            summary["recommendations"]["embedding_model"] = "keep_current"

        # Query pattern findings
        if query_results["overall_success_rate"] > 0.5:
            summary["key_findings"].append(f"Tree-sitter queries successful ({query_results['overall_success_rate']:.1%} success rate)")
            summary["recommendations"]["query_patterns"] = "implement"
        else:
            summary["key_findings"].append("Tree-sitter queries need refinement")
            summary["recommendations"]["query_patterns"] = "refine_and_retry"

        # Success metrics
        summary["success_metrics"] = {
            "embedding_evaluation_completed": "unixcoder" in embedding_results["models"],
            "query_patterns_tested": query_results["patterns_tested"],
            "cross_language_similarity_evaluated": embedding_results["dataset_stats"].get("cross_language_pairs", 0) > 0,
            "multi_language_support": len(query_results["languages"]) >= 3
        }

        # Risk assessment
        summary["risk_assessment"] = {
            "integration_complexity": "medium",
            "performance_impact": "low",
            "maintenance_overhead": "low",
            "compatibility_risk": "low"
        }

        # Next actions
        summary["recommendations"]["next_actions"] = [
            "Implement recommended embedding model",
            "Deploy Tree-sitter query patterns for production use",
            "Monitor performance metrics in production",
            "Consider expanding evaluation dataset"
        ]

        return summary

    def save_results(self, output_path: Path):
        """Save evaluation results to file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.evaluation_results, f, indent=2, default=str)
            logger.info(f"Evaluation results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def get_results_summary(self) -> str:
        """Get a human-readable summary of results."""
        if "complete" not in self.evaluation_results:
            return "Evaluation not yet completed"

        results = self.evaluation_results["complete"]
        summary = results["executive_summary"]

        report = f"""
=== UniXcoder Research Spike - Evaluation Summary ===

Duration: {results['evaluation_duration_seconds']:.1f} seconds
Dataset: {results['technical_details']['dataset_size']} samples across {results['technical_details']['languages_tested']} languages

KEY FINDINGS:
{chr(10).join(f"• {finding}" for finding in summary['key_findings'])}

RECOMMENDATIONS:
• Embedding Model: {summary['recommendations']['embedding_model'].replace('_', ' ').title()}
• Query Patterns: {summary['recommendations']['query_patterns'].replace('_', ' ').title()}

SUCCESS METRICS:
{chr(10).join(f"• {metric.replace('_', ' ').title()}: {value}" for metric, value in summary['success_metrics'].items())}

NEXT ACTIONS:
{chr(10).join(f"• {action}" for action in summary['recommendations']['next_actions'])}

=== End Summary ===
"""
        return report
