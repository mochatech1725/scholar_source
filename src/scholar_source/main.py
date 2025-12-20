#!/usr/bin/env python
import argparse
import sys
import warnings

from scholar_source.crew import ScholarSource

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def parse_arguments():
    """
    Parse command-line arguments for crew inputs.
    All arguments are optional, but at least one must be provided.
    """
    parser = argparse.ArgumentParser(
        description='Run ScholarSource crew to discover educational resources for courses.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -u "MIT" -s "Computer Science"
  %(prog)s --university-name "MIT" --subject "Computer Science"
  %(prog)s -url "https://ocw.mit.edu/courses/6-034-artificial-intelligence-fall-2010/"
  %(prog)s -t "Search algorithms, Machine learning, Neural networks"
        """
    )

    parser.add_argument(
        '-u', '--university-name',
        help='University name for formal courses (e.g., "MIT", "Stanford")'
    )
    parser.add_argument(
        '-s', '--subject',
        help='Subject area (e.g., "Computer Science", "Mathematics")'
    )
    parser.add_argument(
        '-n', '--course-number',
        help='Course identifier (e.g., "6.034", "CS229")'
    )
    parser.add_argument(
        '-url', '--course-url',
        help='Course webpage URL'
    )
    parser.add_argument(
        '-c', '--course-name',
        help='Informal course name (e.g., "Introduction to AI")'
    )
    parser.add_argument(
        '-b', '--textbook',
        help='Textbook information or title'
    )
    parser.add_argument(
        '-syl', '--syllabus',
        help='Syllabus text or URL'
    )
    parser.add_argument(
        '-t', '--topics-list',
        help='Comma-separated list of topics to cover'
    )
    parser.add_argument(
        '-i', '--additional-info',
        help='Any additional information or context'
    )

    return parser.parse_args()

def validate_inputs(inputs):
    """
    Validate that at least one course-related input is provided.

    Args:
        inputs: Dictionary of input values

    Raises:
        ValueError: If no course-related inputs are provided

    Returns:
        The validated inputs dictionary
    """
    # List of course-related input keys (excluding auto-populated fields like current_year)
    course_input_keys = [
        'university_name', 'subject', 'course_number', 'course_url',
        'course_name', 'textbook', 'syllabus', 'topics_list', 'additional_info'
    ]

    # Check if at least one course input is provided
    has_input = any(inputs.get(key) for key in course_input_keys)

    if not has_input:
        error_msg = """
Error: At least one course-related input must be provided.

Available options:
  -u, --university-name    University name for formal courses
  -s, --subject            Subject area
  -n, --course-number      Course identifier
  -url, --course-url       Course webpage URL
  -c, --course-name        Informal course name
  -b, --textbook           Textbook information
  -syl, --syllabus         Syllabus text or URL
  -t, --topics-list        List of topics to cover
  -i, --additional-info    Any additional context

Example usage:
  scholar_source -u "MIT" -s "Computer Science"
  scholar_source --university-name "MIT" --subject "Computer Science"

Use --help for more information.
        """
        raise ValueError(error_msg.strip())

    return inputs

def build_inputs_from_args(args):
    """
    Build inputs dictionary from parsed arguments, excluding None values.

    Args:
        args: Parsed command-line arguments

    Returns:
        Dictionary of inputs with None values filtered out
    """
    inputs = {}

    # Map CLI arguments to input dictionary keys
    arg_mapping = {
        'university_name': args.university_name,
        'subject': args.subject,
        'course_number': args.course_number,
        'course_url': args.course_url,
        'course_name': args.course_name,
        'textbook': args.textbook,
        'syllabus': args.syllabus,
        'topics_list': args.topics_list,
        'additional_info': args.additional_info,
    }

    # Only include non-None values
    for key, value in arg_mapping.items():
        if value is not None:
            inputs[key] = value

    return inputs

def run():
    """
    Run the crew with inputs from command-line arguments.
    """
    try:
        args = parse_arguments()
        inputs = build_inputs_from_args(args)
        validate_inputs(inputs)
        ScholarSource().crew().kickoff(inputs=inputs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    Usage: train <n_iterations> <filename> [--university-name ...] [--subject ...] etc.
    """
    try:
        args = parse_arguments()
        inputs = build_inputs_from_args(args)
        validate_inputs(inputs)
        ScholarSource().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ScholarSource().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    Usage: test <n_iterations> <eval_llm> [--university-name ...] [--subject ...] etc.
    """
    try:
        args = parse_arguments()
        inputs = build_inputs_from_args(args)
        validate_inputs(inputs)
        ScholarSource().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
