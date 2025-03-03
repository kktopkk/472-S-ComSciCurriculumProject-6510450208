import fitz
import re
import unicodedata
from ..models import Enrollment, User, Course
from django.core.exceptions import ObjectDoesNotExist

class OCRService():
    def __init__(self):
        self.courses = {course.course_id: course for course in Course.objects.all()}
        
    def extract_semester(self, item):
        semester_match = re.match(r"(First|Second) Semester (\d{4})", item)
        summer_match = re.match(r"(First|Second)* Summer Session (\d{4})", item)
        
        if semester_match:
            term, year = semester_match.groups()
            return f"{1 if term == 'First' else 2}/{int(year) + 543}"
        elif summer_match:
            _, year = summer_match.groups()
            return f"0/{int(year) - 1 + 543}"
        return None
    
    #NOTE: passing uid
    def extract_course_info(self, text):
        count = 0
        course_data = {}
        current_semester = None

        i = 0
        while i < len(text):
            item = text[i].strip()
            
            semester = self.extract_semester(item)
            if semester:
                current_semester = semester
                course_data.setdefault(current_semester, {})

            # match course id and course name
            course_match = re.match(r"(\d{8})\s+(.+)", item) 
            if course_match and current_semester:
                course_id = course_match.group(1)

                # ถ้าไม่มีเกรดข้ามเรื่อยๆจนกว่าจะเจอเกรด
                g = None
                j = i + 1
                while j < len(text):
                    next_item = text[j].strip()
                    if next_item in ['A', 'B', 'B+', 'C', 'C+', 'D', 'D+', 'F', 'P', 'NP', 'N']:
                        g = next_item
                        break
                    j += 1  

                if g:
                    # s, y = current_semester.split('/')
                    # e = Enrollment(semester=s, year=y, grade=g, user_fk=User.objects.get(user_id=uid), course_fk=self.courses[course_id])
                    # print(e)
                    course_data[current_semester][course_id] = g
                    count += 1
            i += 1  

        print("Total courses:", count)
        return course_data
    
    def get_activiy_status(self, text, uid):
        id_match = re.match(r".+\s+(\d{10})", text[1])
        
        if id_match:
            matched_uid = id_match.group(1)
            
            if matched_uid == uid:
                try:
                    User.objects.get(student_code=uid)
                
                    if "PASS" in text:
                        return True
                    else:
                        return False
                except ObjectDoesNotExist:
                    print(f"User with student_code {uid} not found.")
                    return False
            else:
                return False
        return False
    
    def get_student_info(self, text):
        student_info = {}
        for i, item in enumerate(text):
            match = re.match(r"\s*STUDENT ID\s+(\d{10})", item)
            if match:
                student_info["ID"] = match.group(1)
            
            match = re.match(r"\s*NAME\s+(.+)", item)
            if match:
                student_info["Name"] = match.group(1)
                
            match = re.match(r"\s*FACULTY OF\s+(.+)", item)
            if match:
                student_info["Faculty"] = match.group(1)
            
            match = re.match(r"\s*FIELD OF STUDY\s+(.+)", item)
            if match:
                student_info["Field"] = match.group(1)
                
            match = re.match(r"\s*DATE OF ADMISSION\s+(.+)", item)
            if match:
                student_info["Start_year"] = int(match.group(1).split()[2]) + 543
                
        return student_info

    def extract_text_from_pdf(self, file_path):
        with open(file_path, 'rb') as file:
            doc = fitz.open(file)
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            return text.split("\n")
        
