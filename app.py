# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import pdfplumber
# import re
# import io
# import logging
# from werkzeug.utils import secure_filename
# import os
# import tempfile
# from difflib import SequenceMatcher

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# app = Flask(__name__)
# CORS(app)  # Allow React frontend to communicate with Flask backend

# # Constants
# GRADE_POINTS = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "P": 4, "F": 0}
# ALLOWED_EXTENSIONS = {'pdf'}

# def allowed_file(filename):
#     """Check if file has an allowed extension."""
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def extract_text_from_pdf(pdf_file):
#     """Extract text from a PDF file."""
#     try:
#         text = ""
#         with pdfplumber.open(pdf_file) as pdf:
#             for page in pdf.pages:
#                 text += page.extract_text() + "\n"
#         return text
#     except Exception as e:
#         logger.error(f"PDF extraction error: {str(e)}")
#         raise ValueError("Unable to extract text from the provided PDF")

# def normalize_subject_code(code):
#     """Normalize subject codes to handle variations."""
#     # Remove any spaces in the code
#     code = code.strip().replace(" ", "")
#     # Extract the core elements of the code (dept, semester, type, identifier)
#     match = re.search(r'(\d+)([A-Za-z]+)(\d+)([A-Za-z]+)([A-Za-z0-9]+)', code)
#     if match:
#         return match.group(0)
#     return code

# def extract_core_code_parts(code):
#     """Extract core components of a subject code."""
#     match = re.search(r'(\d+)([A-Za-z]+)(\d+)([A-Za-z]+)', code)
#     if match:
#         year = match.group(1)  # e.g., 23
#         dept = match.group(2)  # e.g., IM, BS, MA
#         sem = match.group(3)   # e.g., 3
#         type_code = match.group(4)  # e.g., PC, BS, AE
#         return year, dept, sem, type_code
#     return None, None, None, None

# def parse_result_data(result_text):
#     """Parse subject codes, names, and grades from the result PDF."""
#     subjects = {}
#     subject_lines = []
    
#     # Extract all lines that contain subject codes and grades
#     lines = result_text.split('\n')
    
#     # First, identify all lines with potential subject codes
#     for i, line in enumerate(lines):
#         if re.search(r'\b2\d[A-Za-z]{2}\d[A-Za-z]{2,7}', line):
#             subject_lines.append((i, line))
    
#     # Process each subject line
#     for i, (line_idx, line) in enumerate(subject_lines):
#         # Extract the subject code
#         code_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)', line)
#         if not code_match:
#             continue
        
#         subject_code = code_match.group(1).strip()
#         remaining_text = line[code_match.end():].strip()
        
#         # Extract subject name - it's the text after the code but before numerical values
#         subject_name = re.sub(r'\s+\d+.*$', '', remaining_text).strip()
#         if not subject_name or subject_name.isdigit():
#             # Try to get name from next line if it's not a subject line
#             if line_idx + 1 < len(lines) and line_idx + 1 not in [idx for idx, _ in subject_lines]:
#                 next_line = lines[line_idx + 1]
#                 if not re.search(r'\b2\d[A-Za-z]{2}\d[A-Za-z]{2,7}', next_line):
#                     subject_name = next_line.strip()
        
#         # Look for grade in the current line
#         grade_match = re.search(r'[0-9]+\s+([OABCPFo+]+)$', line)
#         grade = None
        
#         if grade_match:
#             grade = grade_match.group(1).strip().upper().replace(" ", "")
#         else:
#             # Look in next few lines for the grade
#             for j in range(1, 3):  # Check next 2 lines
#                 if line_idx + j < len(lines):
#                     next_line = lines[line_idx + j]
#                     grade_match = re.search(r'([OABCPFo+]+)$', next_line)
#                     if grade_match and len(next_line) < 20:  # Short line likely only contains grade
#                         grade = grade_match.group(1).strip().upper().replace(" ", "")
#                         break
        
#         # Fix common OCR errors
#         if grade == "O+":
#             grade = "O"  # O doesn't have a + variant
        
#         if grade in GRADE_POINTS:
#             subjects[subject_code] = {
#                 "name": subject_name,
#                 "grade": grade,
#                 "normalized_code": normalize_subject_code(subject_code)
#             }
    
#     # Special case processing for result format with explicit GRADES column
#     for i, line in enumerate(lines):
#         if "GRADES" in line and i < len(lines) - 1:
#             # Look for lines after this header that match pattern with grades
#             for j in range(i+1, min(i+20, len(lines))):
#                 grade_line = lines[j]
#                 # Match pattern: code + subject + numbers + grade
#                 full_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)\s+(.*?)\s+\d+\s+\d+\s+\d+\s+([OABCPFo+]+)', grade_line)
#                 if full_match:
#                     subject_code = full_match.group(1).strip()
#                     subject_name = full_match.group(2).strip()
#                     grade = full_match.group(3).strip().upper().replace(" ", "")
                    
#                     if grade in GRADE_POINTS:
#                         subjects[subject_code] = {
#                             "name": subject_name,
#                             "grade": grade,
#                             "normalized_code": normalize_subject_code(subject_code)
#                         }
    
#     # Extract for specific Biology for Engineers pattern (happens to be problematic)
#     bio_pattern = re.compile(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}(?:BFE|FBE))\s+(Biology\s+for\s+Engineers)', re.IGNORECASE)
#     for line in lines:
#         bio_match = bio_pattern.search(line)
#         if bio_match:
#             subject_code = bio_match.group(1).strip()
#             subject_name = bio_match.group(2).strip()
            
#             # Look for grade in the same line
#             grade_match = re.search(r'([OABCPFo+]+)$', line)
#             if grade_match:
#                 grade = grade_match.group(1).strip().upper().replace(" ", "")
#                 if grade in GRADE_POINTS:
#                     subjects[subject_code] = {
#                         "name": subject_name,
#                         "grade": grade,
#                         "normalized_code": normalize_subject_code(subject_code)
#                     }
    
#     # General case for all lines with Biology for Engineers
#     for i, line in enumerate(lines):
#         if "Biology for Engineers" in line:
#             # Look for subject code in the same line
#             code_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)', line)
#             if code_match:
#                 subject_code = code_match.group(1).strip()
                
#                 # Look for grade in the same line
#                 grade_match = re.search(r'([OABCPFo+]+)$', line)
#                 if grade_match:
#                     grade = grade_match.group(1).strip().upper().replace(" ", "")
#                     if grade in GRADE_POINTS:
#                         subjects[subject_code] = {
#                             "name": "Biology for Engineers",
#                             "grade": grade,
#                             "normalized_code": normalize_subject_code(subject_code)
#                         }
#                 else:
#                     # Look in next few lines for grade
#                     for j in range(1, 3):
#                         if i + j < len(lines):
#                             next_line = lines[i + j]
#                             grade_match = re.search(r'([OABCPFo+]+)$', next_line)
#                             if grade_match and len(next_line) < 20:
#                                 grade = grade_match.group(1).strip().upper().replace(" ", "")
#                                 if grade in GRADE_POINTS:
#                                     subjects[subject_code] = {
#                                         "name": "Biology for Engineers",
#                                         "grade": grade,
#                                         "normalized_code": normalize_subject_code(subject_code)
#                                     }
#                                     break
    
#     logger.info(f"Parsed {len(subjects)} subjects with grades")
#     return subjects

# def parse_course_data(course_text):
#     """Parse subject codes and credits from the course registration PDF."""
#     course_credits = {}
#     subject_names = {}  # To store proper subject names
    
#     # Extract lines containing course codes and credits
#     lines = course_text.split('\n')
    
#     # First pass - look for structured course sections
#     in_course_section = False
#     for i, line in enumerate(lines):
#         if "Course Details" in line or "Course Title" in line:
#             in_course_section = True
#             continue
        
#         if in_course_section and "Total Credits" in line:
#             in_course_section = False
#             continue
            
#         if in_course_section:
#             # Try different formats of course listings
#             patterns = [
#                 # Format: Number, Title, Code, Dept, Term, Credits
#                 r'\d+\s+(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+\w+\s+\d+\s+(\d+(?:\.\d+)?)',
#                 # Format: Title Code Dept Term Credits
#                 r'(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+\w+\s+\d+\s+(\d+(?:\.\d+)?)',
#                 # Simpler format with just code and credits at the end
#                 r'(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+.*?(\d+(?:\.\d+)?)$'
#             ]
            
#             for pattern in patterns:
#                 match = re.search(pattern, line)
#                 if match:
#                     subject_name = match.group(1).strip()
#                     subject_code = match.group(2).strip()
#                     credit = float(match.group(3).strip())
                    
#                     normalized_code = normalize_subject_code(subject_code)
#                     course_credits[subject_code] = credit
#                     course_credits[normalized_code] = credit
#                     subject_names[subject_code] = subject_name
#                     subject_names[normalized_code] = subject_name
#                     break
    
#     # Second pass - look for Biology for Engineers specifically
#     bio_pattern = re.compile(r'(Biology\s+for\s+Engineers)\s+(2\d[A-Za-z0-9]{6,10})', re.IGNORECASE)
#     for line in lines:
#         bio_match = bio_pattern.search(line)
#         if bio_match:
#             subject_name = bio_match.group(1).strip()
#             subject_code = bio_match.group(2).strip()
            
#             # Look for credit in the same line
#             credit_match = re.search(r'(\d+(?:\.\d+)?)$', line)
#             if credit_match:
#                 credit = float(credit_match.group(1).strip())
#                 normalized_code = normalize_subject_code(subject_code)
#                 course_credits[subject_code] = credit
#                 course_credits[normalized_code] = credit
#                 subject_names[subject_code] = subject_name
#                 subject_names[normalized_code] = subject_name
            
#             # Also add an alternative code format to handle BS/IM department differences
#             alt_code = None
#             if "BS" in subject_code:
#                 alt_code = subject_code.replace("BS", "IM")
#             elif "IM" in subject_code:
#                 alt_code = subject_code.replace("IM", "BS")
                
#             if alt_code and credit_match:
#                 credit = float(credit_match.group(1).strip())
#                 normalized_alt_code = normalize_subject_code(alt_code)
#                 course_credits[alt_code] = credit
#                 course_credits[normalized_alt_code] = credit
#                 subject_names[alt_code] = subject_name
#                 subject_names[normalized_alt_code] = subject_name
    
#     # Create a map of subject names to use for matching
#     subject_name_map = {}
#     for code, name in subject_names.items():
#         name_key = name.lower().replace(" ", "")
#         subject_name_map[name_key] = code
    
#     logger.info(f"Parsed {len(course_credits)} subjects with credits and {len(subject_names)} subject names")
#     return course_credits, subject_names, subject_name_map

# def find_matching_code(subject_code, course_credits, subject_names, subject_name_map, result_subject_data):
#     """Find matching subject code using multiple strategies."""
#     normalized_code = normalize_subject_code(subject_code)
    
#     # Direct match with normalized code
#     if normalized_code in course_credits:
#         return normalized_code
    
#     # Try matching by subject name
#     subject_name = result_subject_data["name"].lower().replace(" ", "")
#     if subject_name in subject_name_map:
#         matching_code = subject_name_map[subject_name]
#         if matching_code in course_credits:
#             return matching_code
    
#     # Extract key components of the code
#     year, dept, sem, type_code = extract_core_code_parts(normalized_code)
    
#     if not all([year, dept, sem, type_code]):
#         return None
    
#     # Special case for known variations (based on the example files)
#     if "BFE" in subject_code or "Biology" in result_subject_data["name"]:
#         for code in course_credits:
#             if "BFE" in code or "FBE" in code:
#                 return code
    
#     # Check for codes with same year, semester but different department
#     for code in course_credits:
#         year2, dept2, sem2, type2 = extract_core_code_parts(code)
#         if year2 == year and sem2 == sem:
#             # Same subject different department code
#             if (dept == "BS" and dept2 == "IM") or (dept == "IM" and dept2 == "BS"):
#                 # Further verify with part of the subject name
#                 if result_subject_data["name"] and len(result_subject_data["name"]) > 3:
#                     search_term = result_subject_data["name"].lower().split()[0]
#                     if search_term in subject_names.get(code, "").lower():
#                         return code
    
#     # Try finding partially matching codes
#     core_pattern = f"{year}{sem}{type_code[:1]}"
    
#     for code in course_credits:
#         if core_pattern in code:
#             return code
            
#     # If still no match, try a more flexible approach
#     best_match = None
#     highest_similarity = 0
    
#     for code in course_credits:
#         # Check if the code has the same semester
#         if f"{sem}" in code:
#             # Calculate string similarity
#             similarity = SequenceMatcher(None, normalized_code, code).ratio()
#             if similarity > highest_similarity:
#                 highest_similarity = similarity
#                 best_match = code
    
#     # Only return if the similarity is reasonable
#     if highest_similarity > 0.5:
#         return best_match
    
#     return None

# def combine_data(subjects, course_credits, subject_names, subject_name_map):
#     """Combine data from results and course registration."""
#     combined_data = {}
#     unmatched_subjects = []
    
#     for subject_code, subject_data in subjects.items():
#         credit = None
#         name = subject_data["name"]
#         normalized_code = subject_data["normalized_code"]
        
#         # Try direct match first
#         if subject_code in course_credits:
#             credit = course_credits[subject_code]
#         # Try normalized code
#         elif normalized_code in course_credits:
#             credit = course_credits[normalized_code]
#         # Try finding a similar code
#         else:
#             matching_code = find_matching_code(subject_code, course_credits, subject_names, subject_name_map, subject_data)
#             if matching_code:
#                 credit = course_credits[matching_code]
#                 # Also use better subject name if available
#                 if matching_code in subject_names:
#                     name = subject_names[matching_code]
        
#         if credit is not None:
#             # Get better subject name if available
#             if subject_code in subject_names and (name.isdigit() or not name or len(name) < 3):
#                 name = subject_names[subject_code]
#             elif normalized_code in subject_names and (name.isdigit() or not name or len(name) < 3):
#                 name = subject_names[normalized_code]
            
#             combined_data[subject_code] = {
#                 "name": name,
#                 "credit": credit,
#                 "grade": subject_data["grade"],
#                 "grade_point": GRADE_POINTS.get(subject_data["grade"], 0),
#                 "weighted_points": credit * GRADE_POINTS.get(subject_data["grade"], 0)
#             }
#         else:
#             unmatched_subjects.append({
#                 "code": subject_code,
#                 "name": name,
#                 "grade": subject_data["grade"]
#             })
    
#     # Special handling for problematic subjects like Biology for Engineers
#     if unmatched_subjects:
#         logger.info(f"Unmatched subjects: {len(unmatched_subjects)}")
#         for subj in unmatched_subjects:
#             logger.info(f"  {subj['code']} - {subj['name']} - {subj['grade']}")
            
#             # Manual matching for known problematic subjects
#             if "Biology" in subj["name"]:
#                 biology_codes = [code for code in course_credits if "BFE" in code or "FBE" in code]
#                 if biology_codes:
#                     bio_code = biology_codes[0]
#                     credit = course_credits[bio_code]
#                     name = subject_names.get(bio_code, subj["name"])
#                     combined_data[subj["code"]] = {
#                         "name": name,
#                         "credit": credit,
#                         "grade": subj["grade"],
#                         "grade_point": GRADE_POINTS.get(subj["grade"], 0),
#                         "weighted_points": credit * GRADE_POINTS.get(subj["grade"], 0)
#                     }
    
#     logger.info(f"Combined data for {len(combined_data)} subjects")
#     return combined_data

# def calculate_sgpa(subjects):
#     """Calculate SGPA based on credits and grades."""
#     total_credits = 0
#     weighted_sum = 0
#     subject_points = []

#     for subject_code, data in subjects.items():
#         if "credit" not in data or data["credit"] == 0:
#             continue
            
#         credit = data["credit"]
#         grade = data["grade"]
#         grade_point = GRADE_POINTS.get(grade, 0)
#         weighted_point = credit * grade_point

#         subject_points.append({
#             "code": subject_code,
#             "name": data["name"],
#             "credit": credit,
#             "grade": grade,
#             "grade_point": grade_point,
#             "weighted_point": weighted_point
#         })
        
#         total_credits += credit
#         weighted_sum += weighted_point

#     if total_credits <= 0:
#         return 0, subject_points, total_credits, weighted_sum
    
#     sgpa = weighted_sum / total_credits
#     logger.info(f"Calculated SGPA: {round(sgpa, 2)} (Total credits: {total_credits}, Total points: {weighted_sum})")
#     return round(sgpa, 2), subject_points, total_credits, weighted_sum

# def log_extracted_data(result_text, course_text, subjects, credits):
#     """Log detailed information about extraction for debugging."""
#     logger.info("\n----- EXTRACTION DEBUG INFORMATION -----")
#     logger.info("Result PDF subjects extracted:")
#     for code, data in subjects.items():
#         logger.info(f"  {code} - {data['name']} - {data['grade']} - Normalized: {data['normalized_code']}")
    
#     logger.info("\nCourse PDF credits extracted:")
#     for code, credit in credits.items():
#         if isinstance(credit, (int, float)):
#             logger.info(f"  {code} - {credit}")
    
#     logger.info("-" * 50)

# @app.route("/health", methods=["GET"])
# def health_check():
#     """Simple health check endpoint."""
#     return jsonify({"status": "healthy", "version": "1.2.0"})

# @app.route("/upload", methods=["POST"])
# def upload_files():
#     """Handle file uploads and calculate SGPA."""
#     try:
#         if "results" not in request.files or "courses" not in request.files:
#             return jsonify({"error": "Both course and result PDFs are required"}), 400

#         course_pdf = request.files["courses"]
#         result_pdf = request.files["results"]
        
#         # Validate files
#         for file in [course_pdf, result_pdf]:
#             if file.filename == '':
#                 return jsonify({"error": "No file selected"}), 400
#             if not allowed_file(file.filename):
#                 return jsonify({"error": "File must be a PDF"}), 400

#         logger.info(f"Processing files: {course_pdf.filename}, {result_pdf.filename}")
            
#         # Extract text from both PDFs
#         course_text = extract_text_from_pdf(course_pdf)
#         result_text = extract_text_from_pdf(result_pdf)

#         # Parse data from both files
#         subjects_with_grades = parse_result_data(result_text)
#         if not subjects_with_grades:
#             return jsonify({"error": "No subjects found in the results PDF. Please check the file."}), 400
            
#         course_credits, subject_names, subject_name_map = parse_course_data(course_text)
#         if not course_credits:
#             return jsonify({"error": "No course credits found in the course PDF. Please check the file."}), 400
        
#         # Log detailed extraction information
#         log_extracted_data(result_text, course_text, subjects_with_grades, course_credits)
        
#         # Combine data from both files
#         combined_data = combine_data(subjects_with_grades, course_credits, subject_names, subject_name_map)
#         if not combined_data:
#             return jsonify({"error": "Could not match any subjects between the two files. Please check that both files are for the same semester."}), 400
        
#         # Calculate SGPA with additional info
#         sgpa, subject_points, total_credits, total_points = calculate_sgpa(combined_data)
        
#         # Format for frontend display
#         formatted_subjects = {}
#         for point in subject_points:
#             # Use subject name as key, not subject code
#             subject_name = point["name"]
#             if subject_name.isdigit() or not subject_name:
#                 subject_name = f"Subject {point['code']}"
                
#             formatted_subjects[subject_name] = {
#                 "code": point["code"],
#                 "credit": point["credit"],
#                 "grade": point["grade"],
#                 "grade_point": point["grade_point"],
#                 "weighted_point": round(point["weighted_point"], 2)
#             }

#         # Print detailed calculation to terminal for debugging
#         logger.info("\n----- SGPA CALCULATION SUMMARY -----")
#         logger.info(f"{'SUBJECT CODE':<15} {'SUBJECT NAME':<40} {'CREDITS':<10} {'GRADE':<8} {'POINTS':<8} {'WEIGHTED':<10}")
#         logger.info("-" * 90)
#         for point in subject_points:
#             logger.info(f"{point['code']:<15} {point['name']:<40} {point['credit']:<10.1f} {point['grade']:<8} {point['grade_point']:<8} {point['weighted_point']:<10.1f}")
#         logger.info("-" * 90)
#         logger.info(f"TOTAL CREDITS: {total_credits:.1f}")
#         logger.info(f"TOTAL POINTS: {total_points:.1f}")
#         logger.info(f"SGPA: {sgpa:.2f}")
#         logger.info("-" * 90)

#         # Return response for frontend
#         return jsonify({
#             "sgpa": sgpa,
#             "subjects": formatted_subjects,
#             "summary": {
#                 "total_credits": round(total_credits, 1),
#                 "total_points": round(total_points, 1),
#                 "max_possible_points": round(total_credits * 10, 1),
#                 "percentage": round((total_points / (total_credits * 10)) * 100, 2)
#             }
#         })
        
#     except ValueError as e:
#         logger.error(f"Value error: {str(e)}")
#         return jsonify({"error": str(e)}), 400
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}")
#         return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

# # if __name__ == "__main__":
# #     app.run(debug=True)


# # if __name__ == "__main__":
# #     app.run(debug=True, host='0.0.0.0', port=5000)


# if __name__ == "__main__":
#     app.run()



















from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import re
import io
import logging
from werkzeug.utils import secure_filename
import os
import tempfile
from difflib import SequenceMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

GRADE_POINTS = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "P": 4, "F": 0}
ALLOWED_EXTENSIONS = {'pdf'}

DEPARTMENT_CODES = {
    "CV": "Civil Engineering",
    "ME": "Mechanical Engineering",
    "ES": "Electrical and Electronics Engineering",
    "EC": "Electronics and Communication Engineering",
    "IM": "Industrial Engineering and Management",
    "CS": "Computer Science and Engineering",
    "ET": "Electronics and Telecommunication Engineering",
    "IS": "Information Science and Engineering",
    "EI": "Electronics and Instrumentation Engineering",
    "MD": "Medical Electronics Engineering",
    "CH": "Chemical Engineering",
    "BT": "Bio-Technology",
    "AS": "Aerospace Engineering",
    "AM": "Machine Learning (AI and ML)",
    "DS": "Computer Science and Engineering (DS)",
    "DC": "Computer Science and Engineering (IoT and CS)",
    "AI": "Artificial Intelligence and Data Science",
    "BS": "Computer Science and Business Systems"
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_file):
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        raise ValueError("Unable to extract text from the provided PDF")

def detect_department(result_text, course_text):
    all_text = result_text + course_text
    dept_counts = {}
    
    for dept_code, dept_name in DEPARTMENT_CODES.items():
        pattern = fr'\b2\d{dept_code}\d'
        matches = re.findall(pattern, all_text)
        dept_counts[dept_code] = len(matches)
    
    max_dept = max(dept_counts.items(), key=lambda x: x[1]) if dept_counts else (None, 0)
    
    if max_dept[1] > 0:
        return max_dept[0], DEPARTMENT_CODES.get(max_dept[0])
    
    return None, None

def detect_semester(result_text, course_text):
    all_text = result_text + course_text
    sem_counts = {}
    
    for i in range(1, 9):
        pattern = fr'\b2\d[A-Za-z]{2}{i}[A-Za-z]{2}'
        matches = re.findall(pattern, all_text)
        sem_counts[i] = len(matches)
    
    max_sem = max(sem_counts.items(), key=lambda x: x[1]) if sem_counts else (None, 0)
    
    if max_sem[1] > 0:
        return max_sem[0]
    
    return None

def normalize_subject_code(code):
    code = code.strip().replace(" ", "")
    match = re.search(r'(\d+)([A-Za-z]+)(\d+)([A-Za-z]+)([A-Za-z0-9]+)', code)
    if match:
        return match.group(0)
    return code

def extract_core_code_parts(code):
    match = re.search(r'(\d+)([A-Za-z]+)(\d+)([A-Za-z]+)', code)
    if match:
        year = match.group(1)
        dept = match.group(2)
        sem = match.group(3)
        type_code = match.group(4)
        return year, dept, sem, type_code
    return None, None, None, None

def parse_result_data(result_text):
    subjects = {}
    subject_lines = []
    
    lines = result_text.split('\n')
    
    for i, line in enumerate(lines):
        if re.search(r'\b2\d[A-Za-z]{2}\d[A-Za-z]{2,7}', line):
            subject_lines.append((i, line))
    
    for i, (line_idx, line) in enumerate(subject_lines):
        code_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)', line)
        if not code_match:
            continue
            
        subject_code = code_match.group(1).strip()
        remaining_text = line[code_match.end():].strip()
        
        subject_name = re.sub(r'\s+\d+.*$', '', remaining_text).strip()
        
        if not subject_name or subject_name.isdigit():
            if line_idx + 1 < len(lines) and line_idx + 1 not in [idx for idx, _ in subject_lines]:
                next_line = lines[line_idx + 1]
                if not re.search(r'\b2\d[A-Za-z]{2}\d[A-Za-z]{2,7}', next_line):
                    subject_name = next_line.strip()
        
        grade_match = re.search(r'[0-9]+\s+([OABCPFo+]+)$', line)
        grade = None
        
        if grade_match:
            grade = grade_match.group(1).strip().upper().replace(" ", "")
        else:
            for j in range(1, 3):
                if line_idx + j < len(lines):
                    next_line = lines[line_idx + j]
                    grade_match = re.search(r'([OABCPFo+]+)$', next_line)
                    if grade_match and len(next_line) < 20:
                        grade = grade_match.group(1).strip().upper().replace(" ", "")
                        break
        
        if grade == "O+":
            grade = "O"
            
        if grade in GRADE_POINTS:
            subjects[subject_code] = {
                "name": subject_name,
                "grade": grade,
                "normalized_code": normalize_subject_code(subject_code)
            }
    
    for i, line in enumerate(lines):
        if "GRADES" in line and i < len(lines) - 1:
            for j in range(i+1, min(i+20, len(lines))):
                grade_line = lines[j]
                full_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)\s+(.*?)\s+\d+\s+\d+\s+\d+\s+([OABCPFo+]+)', grade_line)
                
                if full_match:
                    subject_code = full_match.group(1).strip()
                    subject_name = full_match.group(2).strip()
                    grade = full_match.group(3).strip().upper().replace(" ", "")
                    
                    if grade in GRADE_POINTS:
                        subjects[subject_code] = {
                            "name": subject_name,
                            "grade": grade,
                            "normalized_code": normalize_subject_code(subject_code)
                        }
    
    special_subject_patterns = [
        (r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}(?:BFE|FBE))\s+(Biology\s+for\s+Engineers)', "Biology for Engineers"),
        (r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}ENV)\s+(Environmental\s+Studies)', "Environmental Studies"),
        (r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}CPH)\s+(Constitution\s+of\s+India)', "Constitution of India"),
        (r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}MAT)\s+(Mathematics)', "Mathematics")
    ]
    
    for pattern, name in special_subject_patterns:
        for line in lines:
            special_match = re.search(pattern, line, re.IGNORECASE)
            if special_match:
                subject_code = special_match.group(1).strip()
                subject_name = name
                
                grade_match = re.search(r'([OABCPFo+]+)$', line)
                if grade_match:
                    grade = grade_match.group(1).strip().upper().replace(" ", "")
                    if grade in GRADE_POINTS:
                        subjects[subject_code] = {
                            "name": subject_name,
                            "grade": grade,
                            "normalized_code": normalize_subject_code(subject_code)
                        }
    
    for i, line in enumerate(lines):
        for keyword in ["Biology for Engineers", "Environmental Studies", "Constitution of India"]:
            if keyword in line:
                code_match = re.search(r'(2\d[A-Za-z]{2}\d[A-Za-z]{2,7}[A-Za-z0-9]*)', line)
                if code_match:
                    subject_code = code_match.group(1).strip()
                    
                    grade_match = re.search(r'([OABCPFo+]+)$', line)
                    if grade_match:
                        grade = grade_match.group(1).strip().upper().replace(" ", "")
                        if grade in GRADE_POINTS:
                            subjects[subject_code] = {
                                "name": keyword,
                                "grade": grade,
                                "normalized_code": normalize_subject_code(subject_code)
                            }
                    else:
                        for j in range(1, 3):
                            if i + j < len(lines):
                                next_line = lines[i + j]
                                grade_match = re.search(r'([OABCPFo+]+)$', next_line)
                                if grade_match and len(next_line) < 20:
                                    grade = grade_match.group(1).strip().upper().replace(" ", "")
                                    if grade in GRADE_POINTS:
                                        subjects[subject_code] = {
                                            "name": keyword,
                                            "grade": grade,
                                            "normalized_code": normalize_subject_code(subject_code)
                                        }
                                    break
    
    logger.info(f"Parsed {len(subjects)} subjects with grades")
    return subjects

def parse_course_data(course_text):
    course_credits = {}
    subject_names = {}
    
    lines = course_text.split('\n')
    
    in_course_section = False
    for i, line in enumerate(lines):
        if "Course Details" in line or "Course Title" in line:
            in_course_section = True
            continue
            
        if in_course_section and "Total Credits" in line:
            in_course_section = False
            continue
            
        if in_course_section:
            patterns = [
                r'\d+\s+(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+\w+\s+\d+\s+(\d+(?:\.\d+)?)',
                r'(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+\w+\s+\d+\s+(\d+(?:\.\d+)?)',
                r'(.+?)\s+(2\d[A-Za-z0-9]{6,10})\s+.*?(\d+(?:\.\d+)?)$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    subject_name = match.group(1).strip()
                    subject_code = match.group(2).strip()
                    credit = float(match.group(3).strip())
                    
                    normalized_code = normalize_subject_code(subject_code)
                    course_credits[subject_code] = credit
                    course_credits[normalized_code] = credit
                    subject_names[subject_code] = subject_name
                    subject_names[normalized_code] = subject_name
                    break
    
    special_subject_patterns = [
        (r'(Biology\s+for\s+Engineers)\s+(2\d[A-Za-z0-9]{6,10})', "BFE|FBE"),
        (r'(Environmental\s+Studies)\s+(2\d[A-Za-z0-9]{6,10})', "ENV"),
        (r'(Constitution\s+of\s+India)\s+(2\d[A-Za-z0-9]{6,10})', "CPH"),
        (r'(Mathematics)\s+(2\d[A-Za-z0-9]{6,10})', "MAT")
    ]
    
    for pattern, identifier in special_subject_patterns:
        for line in lines:
            special_match = re.search(pattern, line, re.IGNORECASE)
            if special_match:
                subject_name = special_match.group(1).strip()
                subject_code = special_match.group(2).strip()
                
                credit_match = re.search(r'(\d+(?:\.\d+)?)$', line)
                if credit_match:
                    credit = float(credit_match.group(1).strip())
                    normalized_code = normalize_subject_code(subject_code)
                    course_credits[subject_code] = credit
                    course_credits[normalized_code] = credit
                    subject_names[subject_code] = subject_name
                    subject_names[normalized_code] = subject_name
    
    for code in list(course_credits.keys()):
        year, dept, sem, type_code = extract_core_code_parts(code)
        if year and dept and sem:
            credit = course_credits[code]
            name = subject_names.get(code, "")
            
            for alt_dept in DEPARTMENT_CODES:
                if alt_dept != dept:
                    alt_code = code.replace(dept, alt_dept)
                    alt_normalized = normalize_subject_code(alt_code)
                    course_credits[alt_code] = credit
                    course_credits[alt_normalized] = credit
                    subject_names[alt_code] = name
                    subject_names[alt_normalized] = name
    
    subject_name_map = {}
    for code, name in subject_names.items():
        name_key = name.lower().replace(" ", "")
        subject_name_map[name_key] = code
    
    logger.info(f"Parsed {len(course_credits)} subjects with credits and {len(subject_names)} subject names")
    return course_credits, subject_names, subject_name_map

def find_matching_code(subject_code, course_credits, subject_names, subject_name_map, result_subject_data):
    normalized_code = normalize_subject_code(subject_code)
    
    if normalized_code in course_credits:
        return normalized_code
    
    subject_name = result_subject_data["name"].lower().replace(" ", "")
    if subject_name in subject_name_map:
        matching_code = subject_name_map[subject_name]
        if matching_code in course_credits:
            return matching_code
    
    year, dept, sem, type_code = extract_core_code_parts(normalized_code)
    if not all([year, dept, sem, type_code]):
        return None
    
    special_keywords = {
        "BFE": "Biology for Engineers",
        "FBE": "Biology for Engineers",
        "ENV": "Environmental Studies",
        "CPH": "Constitution of India",
        "MAT": "Mathematics"
    }
    
    for keyword, subject in special_keywords.items():
        if keyword in subject_code or subject in result_subject_data["name"]:
            for code in course_credits:
                if keyword in code:
                    return code
    
    for code in course_credits:
        year2, dept2, sem2, type2 = extract_core_code_parts(code)
        if year2 == year and sem2 == sem:
            if result_subject_data["name"] and len(result_subject_data["name"]) > 3:
                search_term = result_subject_data["name"].lower().split()[0]
                if search_term in subject_names.get(code, "").lower():
                    return code
    
    core_pattern = f"{year}{sem}{type_code[:1]}"
    for code in course_credits:
        if core_pattern in code:
            return code
    
    best_match = None
    highest_similarity = 0
    for code in course_credits:
        if f"{sem}" in code:
            similarity = SequenceMatcher(None, normalized_code, code).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = code
    
    if highest_similarity > 0.5:
        return best_match
    
    for code in course_credits:
        year2, dept2, sem2, type2 = extract_core_code_parts(code)
        if sem2 == sem:
            return code
    
    return None

def combine_data(subjects, course_credits, subject_names, subject_name_map):
    combined_data = {}
    unmatched_subjects = []
    
    for subject_code, subject_data in subjects.items():
        credit = None
        name = subject_data["name"]
        normalized_code = subject_data["normalized_code"]
        
        if subject_code in course_credits:
            credit = course_credits[subject_code]
        elif normalized_code in course_credits:
            credit = course_credits[normalized_code]
        else:
            matching_code = find_matching_code(subject_code, course_credits, subject_names, subject_name_map, subject_data)
            if matching_code:
                credit = course_credits[matching_code]
                
                if matching_code in subject_names:
                    name = subject_names[matching_code]
        
        if credit is not None:
            if subject_code in subject_names and (name.isdigit() or not name or len(name) < 3):
                name = subject_names[subject_code]
            elif normalized_code in subject_names and (name.isdigit() or not name or len(name) < 3):
                name = subject_names[normalized_code]
            
            combined_data[subject_code] = {
                "name": name,
                "credit": credit,
                "grade": subject_data["grade"],
                "grade_point": GRADE_POINTS.get(subject_data["grade"], 0),
                "weighted_points": credit * GRADE_POINTS.get(subject_data["grade"], 0)
            }
        else:
            unmatched_subjects.append({
                "code": subject_code,
                "name": name,
                "grade": subject_data["grade"]
            })
    
    if unmatched_subjects:
        logger.info(f"Unmatched subjects: {len(unmatched_subjects)}")
        
        for subj in unmatched_subjects:
            logger.info(f" {subj['code']} - {subj['name']} - {subj['grade']}")
            
            # Handle special cases
            for keyword, pattern in [
                ("Biology", r"BFE|FBE"),
                ("Environment", r"ENV"),
                ("Constitution", r"CPH"),
                ("Math", r"MAT")
            ]:
                if keyword in subj["name"]:
                    matching_codes = [code for code in course_credits if re.search(pattern, code)]
                    if matching_codes:
                        code = matching_codes[0]
                        credit = course_credits[code]
                        name = subject_names.get(code, subj["name"])
                        
                        combined_data[subj["code"]] = {
                            "name": name,
                            "credit": credit,
                            "grade": subj["grade"],
                            "grade_point": GRADE_POINTS.get(subj["grade"], 0),
                            "weighted_points": credit * GRADE_POINTS.get(subj["grade"], 0)
                        }
                        break
            
            # Try to match by semester and type
            year, dept, sem, type_code = extract_core_code_parts(subj["code"])
            if sem:
                for code in course_credits:
                    _, _, code_sem, code_type = extract_core_code_parts(code)
                    if code_sem == sem and (type_code == code_type or type_code[0] == code_type[0]):
                        credit = course_credits[code]
                        name = subject_names.get(code, subj["name"])
                        
                        combined_data[subj["code"]] = {
                            "name": name,
                            "credit": credit,
                            "grade": subj["grade"],
                            "grade_point": GRADE_POINTS.get(subj["grade"], 0),
                            "weighted_points": credit * GRADE_POINTS.get(subj["grade"], 0)
                        }
                        break
    
    logger.info(f"Combined data for {len(combined_data)} subjects")
    return combined_data

def calculate_sgpa(subjects):
    total_credits = 0
    weighted_sum = 0
    subject_points = []
    
    for subject_code, data in subjects.items():
        if "credit" not in data or data["credit"] == 0:
            continue
            
        credit = data["credit"]
        grade = data["grade"]
        grade_point = GRADE_POINTS.get(grade, 0)
        weighted_point = credit * grade_point
        
        subject_points.append({
            "code": subject_code,
            "name": data["name"],
            "credit": credit,
            "grade": grade,
            "grade_point": grade_point,
            "weighted_point": weighted_point
        })
        
        total_credits += credit
        weighted_sum += weighted_point
    
    if total_credits <= 0:
        return 0, subject_points, total_credits, weighted_sum
        
    sgpa = weighted_sum / total_credits
    logger.info(f"Calculated SGPA: {round(sgpa, 2)} (Total credits: {total_credits}, Total points: {weighted_sum})")
    
    return round(sgpa, 2), subject_points, total_credits, weighted_sum

def generate_report(subject_points, sgpa, total_credits, total_points, dept_code, dept_name, semester):
    report = {
        "sgpa": sgpa,
        "department": {
            "code": dept_code,
            "name": dept_name
        },
        "semester": semester,
        "subjects": {},
        "summary": {
            "total_credits": round(total_credits, 1),
            "total_points": round(total_points, 1),
            "max_possible_points": round(total_credits * 10, 1),
            "percentage": round((total_points / (total_credits * 10)) * 100, 2)
        }
    }
    
    for point in subject_points:
        subject_name = point["name"]
        if subject_name.isdigit() or not subject_name:
            subject_name = f"Subject {point['code']}"
            
        report["subjects"][subject_name] = {
            "code": point["code"],
            "credit": point["credit"],
            "grade": point["grade"],
            "grade_point": point["grade_point"],
            "weighted_point": round(point["weighted_point"], 2)
        }
    
    return report

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "version": "2.0.0"})

@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        if "results" not in request.files or "courses" not in request.files:
            return jsonify({"error": "Both course and result PDFs are required"}), 400
            
        course_pdf = request.files["courses"]
        result_pdf = request.files["results"]
        
        for file in [course_pdf, result_pdf]:
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            if not allowed_file(file.filename):
                return jsonify({"error": "File must be a PDF"}), 400
                
        logger.info(f"Processing files: {course_pdf.filename}, {result_pdf.filename}")
        
        course_text = extract_text_from_pdf(course_pdf)
        result_text = extract_text_from_pdf(result_pdf)
        
        # Detect department and semester
        dept_code, dept_name = detect_department(result_text, course_text)
        semester = detect_semester(result_text, course_text)
        
        if not dept_code:
            logger.warning("Could not automatically detect department")
        else:
            logger.info(f"Detected department: {dept_code} ({dept_name})")
            
        if not semester:
            logger.warning("Could not automatically detect semester")
        else:
            logger.info(f"Detected semester: {semester}")
        
        subjects_with_grades = parse_result_data(result_text)
        if not subjects_with_grades:
            return jsonify({"error": "No subjects found in the results PDF. Please check the file."}), 400
            
        course_credits, subject_names, subject_name_map = parse_course_data(course_text)
        if not course_credits:
            return jsonify({"error": "No course credits found in the course PDF. Please check the file."}), 400
            
        combined_data = combine_data(subjects_with_grades, course_credits, subject_names, subject_name_map)
        if not combined_data:
            return jsonify({"error": "Could not match any subjects between the two files. Please check that both files are for the same semester."}), 400
            
        sgpa, subject_points, total_credits, total_points = calculate_sgpa(combined_data)
        
        # Generate detailed report
        report = generate_report(subject_points, sgpa, total_credits, total_points, dept_code, dept_name, semester)
        
        # Log detailed calculation
        logger.info("\n----- SGPA CALCULATION SUMMARY -----")
        logger.info(f"{'SUBJECT CODE':<15} {'SUBJECT NAME':<40} {'CREDITS':<10} {'GRADE':<8} {'POINTS':<8} {'WEIGHTED':<10}")
        logger.info("-" * 90)
        
        for point in subject_points:
            logger.info(f"{point['code']:<15} {point['name']:<40} {point['credit']:<10.1f} {point['grade']:<8} {point['grade_point']:<8} {point['weighted_point']:<10.1f}")
            
        logger.info("-" * 90)
        logger.info(f"DEPARTMENT: {dept_name if dept_name else 'Unknown'}")
        logger.info(f"SEMESTER: {semester if semester else 'Unknown'}")
        logger.info(f"TOTAL CREDITS: {total_credits:.1f}")
        logger.info(f"TOTAL POINTS: {total_points:.1f}")
        logger.info(f"SGPA: {sgpa:.2f}")
        logger.info("-" * 90)
        
        return jsonify(report)
        
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

if __name__ == "__main__":
    app.run()




