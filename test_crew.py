#!/usr/bin/env python
"""Quick test script to verify crew is working with verbose output."""
import sys
import warnings
from scholar_source.crew import ScholarSource

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def test_crew():
    print("=" * 60)
    print("Starting ScholarSource Crew Test")
    print("=" * 60)
    print("\n[INFO] Initializing crew...")

    try:
        crew_instance = ScholarSource()
        print("[INFO] Crew initialized successfully")

        print("\n[INFO] Starting crew execution...")
        print("[INFO] This may take 1-5 minutes...\n")

        inputs = {
            'university_name': 'MIT',
            'subject': 'Computer Science',
            'course_number': '',
            'course_url': '',
            'course_name': '',
            'textbook': '',
            'syllabus': '',
            'topics_list': '',
            'additional_info': ''
        }

        print(f"[INFO] Inputs: {inputs}\n")

        # Force stdout flush
        sys.stdout.flush()

        result = crew_instance.crew().kickoff(inputs=inputs)

        print("\n" + "=" * 60)
        print("Crew Execution Complete!")
        print("=" * 60)
        print(f"\nResult type: {type(result)}")
        print(f"Result preview: {str(result)[:200]}...")

        return result

    except Exception as e:
        print(f"\n[ERROR] Failed to run crew: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_crew()
