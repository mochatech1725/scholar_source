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
        description="Run ScholarSource crew to discover educational resources similar to your course book.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --book-title "Introduction to Algorithms" --book-author "Cormen, Leiserson, Rivest, Stein"
  %(prog)s --isbn "978-0262046305"
  %(prog)s --book-url "https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/"
  %(prog)s --course-info-url "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"
  %(prog)s --book-pdf-path "/path/to/textbook.pdf"
  %(prog)s -u "MIT" -c "Introduction to Algorithms" --book-title "Introduction to Algorithms"
        """,
    )

    parser.add_argument("-u", "--university-name", help='University name (e.g., "MIT", "Stanford")')
    parser.add_argument("-c", "--course-name", help='Course name (e.g., "Introduction to Algorithms")')
    parser.add_argument("-url", "--course-url", help="Course webpage URL")
    parser.add_argument(
        "-b", "--textbook", help="Textbook information (legacy field, prefer --book-title and --book-author)"
    )
    parser.add_argument("-t", "--topics-list", help="Comma-separated list of topics to cover")
    parser.add_argument("--book-title", help='Book title (e.g., "Introduction to Algorithms")')
    parser.add_argument("--book-author", help='Book author(s) (e.g., "Cormen, Leiserson, Rivest, Stein")')
    parser.add_argument("--isbn", help='ISBN of the book (e.g., "978-0262046305")')
    parser.add_argument("--book-pdf-path", help="Local path to PDF copy of the course book")
    parser.add_argument("--book-url", help="Online link to the book (e.g., publisher website, Amazon, etc.)")

    return parser.parse_args()


def validate_inputs(inputs):
    """
    Validate that required input combinations are provided.

    Required combinations (at least one must be satisfied):
    1. (course_name OR university_name) OR course_url
    2. OR (book_title AND book_author) OR isbn
    3. OR book_pdf_path
    4. OR book_url

    Args:
        inputs: Dictionary of input values

    Raises:
        ValueError: If no valid input combination is provided

    Returns:
        The validated inputs dictionary
    """
    # Check for valid input combinations
    has_course_info = (inputs.get("course_name") and inputs.get("university_name")) or inputs.get("course_url")

    has_book_info = (inputs.get("book_title") and inputs.get("book_author")) or inputs.get("isbn")

    has_book_file = bool(inputs.get("book_pdf_path"))
    has_book_link = bool(inputs.get("book_url"))

    # At least one combination must be satisfied
    is_valid = has_course_info or has_book_info or has_book_file or has_book_link

    if not is_valid:
        error_msg = """
Error: You must provide one of the following input combinations:

Required combinations (at least one):
  1. Course information:
     - (--course-name OR --university-name) OR --course-url
  2. Book identification:
     - (--book-title AND --book-author) OR --isbn
  3. Book file:
     - --book-pdf-path
  4. Book link:
     - --book-url

Example usage:
  scholar_source --book-title "Introduction to Algorithms" --book-author "Cormen, Leiserson, Rivest, Stein"
  scholar_source --isbn "978-0262046305"
  scholar_source --book-url "https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/"
  scholar_source --book-pdf-path "/path/to/textbook.pdf"
  scholar_source -u "MIT" -c "Introduction to Algorithms"
  scholar_source --course-url "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"

Use --help for more information.
        """
        raise ValueError(error_msg.strip())

    return inputs


def build_inputs_from_args(args):
    """
    Build inputs dictionary from parsed arguments.
    All keys are included with empty strings as defaults for unprovided values.

    Args:
        args: Parsed command-line arguments

    Returns:
        Dictionary of inputs with all keys present (empty string if not provided)
    """
    # Map CLI arguments to input dictionary keys
    arg_mapping = {
        "university_name": args.university_name,
        "course_name": args.course_name,
        "course_url": args.course_url,
        "textbook": args.textbook,
        "topics_list": args.topics_list,
        "book_title": args.book_title,
        "book_author": args.book_author,
        "isbn": args.isbn,
        "book_pdf_path": args.book_pdf_path,
        "book_url": args.book_url,
    }

    # Include all keys, using empty string for None values
    # This is required because CrewAI task descriptions reference all variables
    inputs = {key: (value if value is not None else "") for key, value in arg_mapping.items()}

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
        raise RuntimeError(f"An error occurred while running the crew: {e}") from e


def train():
    """
    Train the crew for a given number of iterations.
    Usage: train <n_iterations> <filename> [--university-name ...] [--book-title ...] etc.
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
        raise RuntimeError(f"An error occurred while training the crew: {e}") from e


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ScholarSource().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise RuntimeError(f"An error occurred while replaying the crew: {e}") from e


def test():
    """
    Test the crew execution and returns the results.
    Usage: test <n_iterations> <eval_llm> [--university-name ...] [--book-title ...] etc.
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
        raise RuntimeError(f"An error occurred while testing the crew: {e}") from e
