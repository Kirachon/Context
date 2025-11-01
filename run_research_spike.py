#!/usr/bin/env python3
"""
UniXcoder Research Spike Execution Script

Runs the complete evaluation comparing UniXcoder vs sentence-transformers
and demonstrates Tree-sitter query patterns on real parsed code.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from research.evaluation_suite import EvaluationSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run the complete research spike evaluation."""
    print("🔬 UniXcoder Research Spike - Starting Evaluation")
    print("=" * 60)
    
    try:
        # Initialize evaluation suite
        print("📊 Initializing evaluation suite...")
        suite = EvaluationSuite()
        
        # Run complete evaluation
        print("🚀 Running complete evaluation...")
        results = suite.run_complete_evaluation()
        
        # Save results
        output_path = Path("research_spike_results.json")
        suite.save_results(output_path)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 EVALUATION COMPLETE")
        print("=" * 60)
        print(suite.get_results_summary())
        
        # Print detailed findings
        print("\n" + "=" * 60)
        print("📈 DETAILED FINDINGS")
        print("=" * 60)
        
        # Embedding comparison results
        embedding_results = results["embedding_comparison"]
        print(f"\n🤖 EMBEDDING MODEL COMPARISON:")
        print(f"Dataset: {embedding_results['dataset_stats']['total_samples']} samples, {embedding_results['dataset_stats']['total_similarity_pairs']} similarity pairs")
        
        for model_name, model_results in embedding_results["models"].items():
            if "error" not in model_results:
                print(f"\n{model_name.upper()}:")
                print(f"  • F1 Score: {model_results['f1_score']:.3f}")
                print(f"  • Similarity Accuracy: {model_results['avg_similarity_accuracy']:.3f}")
                print(f"  • Cross-language Accuracy: {model_results['cross_language_accuracy']:.3f}")
                print(f"  • Encoding Time: {model_results['encoding_time_ms']:.1f}ms")
                print(f"  • Memory Usage: {model_results['memory_usage_mb']:.1f}MB")
            else:
                print(f"\n{model_name.upper()}: ❌ {model_results['error']}")
        
        # Query pattern results
        query_results = results["query_pattern_evaluation"]
        print(f"\n🔍 TREE-SITTER QUERY PATTERNS:")
        print(f"Overall Success Rate: {query_results['overall_success_rate']:.1%}")
        print(f"Patterns Tested: {query_results['patterns_tested']}")
        print(f"Successful Matches: {query_results['successful_matches']}")
        
        print(f"\nBy Language:")
        for lang, lang_results in query_results["languages"].items():
            success_rate = lang_results["successful_matches"] / max(lang_results["samples_tested"], 1)
            print(f"  • {lang.title()}: {success_rate:.1%} success ({lang_results['successful_matches']}/{lang_results['samples_tested']} samples)")
        
        print(f"\nTop Performing Patterns:")
        pattern_effectiveness = query_results["pattern_effectiveness"]
        sorted_patterns = sorted(
            pattern_effectiveness.items(), 
            key=lambda x: x[1]["success_rate"], 
            reverse=True
        )
        
        for pattern_name, effectiveness in sorted_patterns[:5]:
            print(f"  • {pattern_name}: {effectiveness['success_rate']:.1%} success rate")
        
        # Recommendations
        recommendations = embedding_results["recommendations"]
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"Primary Recommendation: {recommendations['primary_recommendation'].replace('_', ' ').title()}")
        
        if recommendations["reasoning"]:
            print("Reasoning:")
            for reason in recommendations["reasoning"]:
                print(f"  • {reason}")
        
        print(f"\nNext Steps:")
        for step in recommendations["next_steps"]:
            print(f"  • {step}")
        
        # Final status
        print("\n" + "=" * 60)
        print("✅ Research Spike Complete!")
        print(f"📄 Detailed results saved to: {output_path}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Research spike failed: {e}", exc_info=True)
        print(f"\n❌ Research spike failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
