"""
================================================================================
 Module: answerChecker.py
 Description: 
        Contains logic for validating student answers against correct ones,
        including inline, fraction, variable, and speech-based answers.
 Author: Dominik Horut (xhorut01)
================================================================================
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
import math
import re
from .models import StudentExample, Answer

# Configuration of Gemini API
from be.settings import GEMINI_API_KEY
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)

# Exception for handling Gemini API rate limits
class GeminiRateLimitError(Exception):
    pass

# Base class for all answer-checking logic
class AnswerChecker:

    @staticmethod
    def is_valid_answer(answer):
            # Validates if the answer only contains digits, commas, periods, or minus signs
            return bool(re.match(r'^[0-9,.-]+$', answer))

    @staticmethod
    def updateRecord(student_id, example_id, date, duration, correct, session_id=None):
        # Updates the students attempt record for a example and returns if new example can be displayed
        if student_id:
            record = get_object_or_404(StudentExample, student__id=student_id, example_id=example_id, date=date)
        elif session_id:
            record = get_object_or_404(StudentExample, anonymous_session__session_id=session_id, example_id=example_id, date=date)
        else:
            raise ValueError("Either student_id or session_id must be provided")

        try:
            with transaction.atomic():
                record.attempts += 1

            record.duration = duration

            record.solved = correct

            record.save()

            # If the student made 3 attempts or the answer is correct, new example can be displayed
            return record.attempts == 3 or correct

        except Exception as e:
            print({"error": str(e)})

    @staticmethod
    def compareAnswers(student_answer, correct_answer):
        # Compares two answers numerically
        return math.isclose(correct_answer, student_answer, rel_tol=1e-9)
    

    @staticmethod
    def compareAnswersWithGemini(correct_answer, student_answer, prompt):
        # Uses Gemini API to compare students answer transcription with correct answer
        try:
            model = genai.GenerativeModel("gemini-2.0-flash") 
            response = model.generate_content(prompt)

            # Check for API rate limit to use different class for evaluation
            if "quota" in response.text.lower() or "limit" in response.text.lower():
                raise GeminiRateLimitError("API rate limit reached")

            if(response.text.strip().lower() == "true"):
                return True
            else:
                return False 
        
        except Exception as e:
            # Check for API rate limit to use different class for evaluation
            if "429" in str(e) or "quota" in str(e).lower():
                raise GeminiRateLimitError("API rate limit reached")
            else:
                raise 
        
# Checks inline numerical answers
class InlineAnswerChecker(AnswerChecker):
    pass

    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):   

        correct_answer = Answer.objects.get(example_id=example_id).answer
        
        # Normalize decimal format first (strip spaces e.g. '3 500' -> '3500', commas -> dots)
        student_answer_norm = student_answer.replace(' ', '').replace(',', '.') if student_answer else ''
        correct_answer_norm = correct_answer.replace(' ', '').replace(',', '.')

        # If correct answer is not numeric (e.g. Roman numerals, yes/no), do text comparison
        if not InlineAnswerChecker.is_valid_answer(correct_answer_norm):
            def normalize_text(s):
                s = s.strip().lower()
                s = s.replace('á', 'a').replace('é', 'e').replace('í', 'i')
                s = s.replace('ó', 'o').replace('ú', 'u').replace('č', 'c')
                s = s.replace('š', 's').replace('ž', 'z').replace('ľ', 'l')
                if s in ('ano', 'je', 'yes', 'true', '1', 'pravda'): s = 'ano'
                if s in ('nie', 'nie je', 'neni', 'no', 'false', '0', 'nepravda'): s = 'nie'
                return s
            is_correct = bool(student_answer_norm) and normalize_text(student_answer_norm) == normalize_text(correct_answer_norm)
            continue_with_next = AnswerChecker.updateRecord(student_id, example_id, date, duration, is_correct, session_id=session_id)
            return (is_correct, continue_with_next)

        # Validate numeric answer
        if not InlineAnswerChecker.is_valid_answer(student_answer_norm) or not student_answer_norm:
            continue_with_next = AnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next)

        correct_answer = float(correct_answer_norm)
        student_answer = float(student_answer_norm)

        # Compare and update record
        if AnswerChecker.compareAnswers(student_answer, correct_answer):
            # Correct answer
            continue_with_next = AnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
            return (True, continue_with_next)
        else:
            # Incorrect answer
            continue_with_next = AnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next)

# Checks fraction-based answers
class FractionAnswerChecker(AnswerChecker):
    pass

    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):   

        correct_answer = Answer.objects.get(example_id=example_id).answer

        match = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", correct_answer)

        # Extract numerator and denominator from the correct answers
        if match:
            correct_numerator = float(match.group(1).replace(',', '.'))
            correct_denominator = float(match.group(2).replace(',', '.'))
        else:
            print("Invalid fraction format.")
        
        # Validate students answer and extract numerator and denominator  
        if(FractionAnswerChecker.is_valid_answer(student_answer[0]) and FractionAnswerChecker.is_valid_answer(student_answer[1])):  
            student_numerator = float(student_answer[0].replace(',', '.'))
            student_denominator = float(student_answer[1].replace(',', '.'))
        else:
            continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next)
        
        student_answer = student_numerator / student_denominator
        correct_answer = correct_numerator / correct_denominator

        # Compare and update record
        if AnswerChecker.compareAnswers(correct_answer, student_answer):
            # Correct answer
            continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
            return (True, continue_with_next)
        else:
            # Incorrect answer
            continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next)

# Checks variable-based answers
class VariableAnswerChecker(AnswerChecker):
    pass

    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):   

        correct_answer = Answer.objects.get(example_id=example_id).answer

        # Extract variables and their values from the correct answer
        correct_variables = correct_answer.split(';')
        correct_variables = [variable.strip() for variable in correct_variables if variable.strip()]

        correct_values = []
        student_values = []

        # Extract the correct values from the correct answer
        for variable in correct_variables:
            value = variable.split('=')[1].strip()
            correct_values.append(float(value.replace(',', '.'))) 

        # Validate and extract values from the students answer
        for value in student_answer:

            if not value or not VariableAnswerChecker.is_valid_answer(value):
                continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
                return (False, continue_with_next)

            student_values.append(float(value.replace(',', '.')))
        
        # Compare each value
        for i in range(len(correct_values)):

            if not AnswerChecker.compareAnswers(correct_values[i], student_values[i]):
                # One of the values does not match - incorrect answer
                continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
                return (False, continue_with_next)

        # All values match - correct answer
        continue_with_next = FractionAnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
        return (True, continue_with_next)

# Checks spoken inline numeric answers            
class InlineSpeechAnswerChecker(AnswerChecker):
    
    # Mapping of Slovak/Czech comparison words to symbols
    COMPARISON_WORDS = {
        'väčšie': '>', 'vacsie': '>', 'väčšie než': '>', 'väčšie ako': '>',
        'väčšie nez': '>', 'vacsie nez': '>', 'vacsie ako': '>',
        'vetšie': '>', 'vetsie': '>', 'vetšie než': '>', 'vetšie ako': '>',
        'vetsie nez': '>', 'vetsie ako': '>',
        'menšie': '<', 'mensie': '<', 'menšie než': '<', 'menšie ako': '<',
        'menšie nez': '<', 'mensie nez': '<', 'mensie ako': '<',
        'menšie nako': '<', 'mensie nako': '<',
        'rovné': '=', 'rovne': '=', 'rovná sa': '=', 'rovna sa': '=',
        'rovná': '=', 'rovna': '=', 'rovnajú sa': '=', 'rovnaju sa': '=',
        'rovná se': '=', 'rovna se': '=', 'rovnajú se': '=', 'rovnaju se': '=',
        'je rovné': '=', 'je rovne': '=', 'je rovná': '=', 'je rovna': '=',
        'je väčšie': '>', 'je vacsie': '>', 'je vetšie': '>', 'je vetsie': '>',
        'je menšie': '<', 'je mensie': '<',
        'väčší': '>', 'vacsi': '>', 'vetší': '>', 'vetsi': '>',
        'menší': '<', 'mensi': '<',
        'rovný': '=', 'rovny': '=',
    }

    @staticmethod
    def normalize_text(text):
        """Normalize text by removing extra spaces and converting to lowercase."""
        return ' '.join(text.lower().strip().split())

    @staticmethod
    def extract_comparison_symbol(student_answer):
        """Try to extract comparison symbol from Slovak/Czech spoken words."""
        normalized_answer = InlineSpeechAnswerChecker.normalize_text(student_answer)
        
        # Try to find comparison words in the answer
        # Check longest phrases first to avoid partial matches
        sorted_phrases = sorted(InlineSpeechAnswerChecker.COMPARISON_WORDS.keys(), 
                               key=len, reverse=True)
        
        for phrase in sorted_phrases:
            if phrase in normalized_answer:
                return InlineSpeechAnswerChecker.COMPARISON_WORDS[phrase]
        
        # Check if answer already contains a comparison symbol
        if '>' in student_answer:
            return '>'
        elif '<' in student_answer:
            return '<'
        elif '=' in student_answer:
            return '='
        
        return None

    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):   
        correct_answer = Answer.objects.get(example_id=example_id).answer

        # Check if this is a comparison operator question
        if correct_answer in ['<', '>', '=']:
            extracted_symbol = InlineSpeechAnswerChecker.extract_comparison_symbol(student_answer)
            
            if extracted_symbol is None:
                continue_with_next = InlineSpeechAnswerChecker.updateRecord(
                    student_id, example_id, date, duration, False, session_id=session_id
                )
                return (False, continue_with_next, None)
            
            is_correct = (extracted_symbol == correct_answer)
            continue_with_next = InlineSpeechAnswerChecker.updateRecord(
                student_id, example_id, date, duration, is_correct, session_id=session_id
            )
            return (is_correct, continue_with_next, extracted_symbol)

        # Original numeric answer logic
        try:
            correct_answer = float(correct_answer.replace(",", "."))
        except ValueError:
            return (False, False)

        student_answer = student_answer.replace(",", ".")

        # Extract all numbers from the spoken answer
        numbers_in_answer = re.findall(r'\d+\.\d+|\d+', student_answer)
        extracted_numbers = [float(num) for num in numbers_in_answer]

        # Use only the last extracted number from Azure transcription string
        if not extracted_numbers:
            continue_with_next = InlineSpeechAnswerChecker.updateRecord(
                student_id, example_id, date, duration, False, session_id=session_id
            )
            return (False, continue_with_next, None)

        correct_number = extracted_numbers[-1]
        is_correct = AnswerChecker.compareAnswers(correct_number, correct_answer)

        continue_with_next = InlineSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, is_correct, session_id=session_id)

        return (is_correct, continue_with_next, correct_number)

# Checks spoken fraction-based answers
class FractionSpeechAnswerChecker(AnswerChecker):

    @staticmethod
    def extract_fraction_from_text(student_answer):
        """Extract numerator/denominator pair from speech transcript digits."""
        numbers_in_answer = re.findall(r'\d+\.\d+|\d+', student_answer or "")
        if len(numbers_in_answer) < 2:
            return None

        # Use the last pair - transcript may contain extra numbers/noise.
        numerator = numbers_in_answer[-2].replace(',', '.')
        denominator = numbers_in_answer[-1].replace(',', '.')

        try:
            numerator_f = float(numerator)
            denominator_f = float(denominator)
        except ValueError:
            return None

        if denominator_f == 0:
            return None

        return {"numerator": numerator_f, "denominator": denominator_f}

    @staticmethod
    def extract_fraction_from_latex(correct_answer):
        """Extract numerator/denominator from LaTeX fraction answer (\\frac{a}{b})."""
        match = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", correct_answer or "")
        if not match:
            return None

        numerator = float(match.group(1).replace(',', '.'))
        denominator = float(match.group(2).replace(',', '.'))
        if denominator == 0:
            return None

        return {"numerator": numerator, "denominator": denominator}
    
    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):   
        correct_answer = Answer.objects.get(example_id=example_id).answer
        print(student_answer)
        match = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", correct_answer)
        
        # Extract numerator and denominator from the correct answers
        if match:
            correct_numerator = float(match.group(1).replace(',', '.'))
            correct_denominator = float(match.group(2).replace(',', '.'))
        else:
            return (False, False) 

        parsed = FractionSpeechAnswerChecker.extract_fraction_from_text(student_answer)
        if not parsed:
            continue_with_next = FractionSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next, {"numerator": "", "denominator": ""})

        student_numerator = parsed["numerator"]
        student_denominator = parsed["denominator"]

        if (AnswerChecker.compareAnswers(correct_numerator, student_numerator) and
                AnswerChecker.compareAnswers(correct_denominator, student_denominator)):
            continue_with_next = FractionSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
            return (True, continue_with_next, {"numerator": student_numerator, "denominator": student_denominator})

        continue_with_next = FractionSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
        return (False, continue_with_next, {"numerator": student_numerator, "denominator": student_denominator})

# Checks spoken variable-based answers
class VariableSpeechAnswerChecker(AnswerChecker):
    
    @staticmethod   
    def verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=None):

        correct_answer = Answer.objects.get(example_id=example_id).answer
        correct_variables = correct_answer.split(';')
        correct_variables = [variable.strip() for variable in correct_variables if variable.strip()]

        correct_values = []
        student_values = []
        
        # Extract the values from the correct answer
        for variable in correct_variables:
            value = variable.split('=')[1].strip()  # Extract value after '='
            correct_values.append(float(value.replace(',', '.')))  # Store as float

        # Extract values from the spoken answer
        student_matches = re.findall(r"([a-zA-Z]+)\s*(rovná se|je)\s*([\d,]+)", student_answer, re.IGNORECASE)
        
        for match in student_matches:
            student_value_str = match[2].replace(',', '.')  
            try:
                student_value = float(student_value_str) 
            except ValueError:
                student_value = 0.0
            student_values.append(student_value)

        # Compare sorted lists of values
        if sorted(correct_values) == sorted(student_values): 
            # All values match - correct answer
            continue_with_next = VariableSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
            return (True, continue_with_next, student_values)
        else:
            # One of the values does not match - incorrect answer
            continue_with_next = VariableSpeechAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next, student_values)

# Checks spoken answer using LLM (Gemini)
class LLMAnswerChecker(AnswerChecker):
    
    @staticmethod
    def verifyAnswer(student_id, example_id, date, duration, student_answer, input_type, session_id=None):
        correct_answer = Answer.objects.get(example_id=example_id).answer

        # Choose prompt based on the input type
        if input_type == "fraction":
            prompt = f"""There is a math example with answer written in Latex: {correct_answer}, the user told the answer by voice in czech language: {student_answer}. 
                         Is the users answer correct? Answer just true or false."""
        elif input_type == "variable":
            prompt = f"""Evaluate LaTeX math answer. 
                        Correct answer in LaTeX: {correct_answer}
                        User's Czech voice answer: {student_answer}

                        Rules:
                        - Match each variable name exactly
                        - Compare all variable values
                        - Case-sensitive comparison

                        Respond only "true" or "false"."""

        is_correct = LLMAnswerChecker.compareAnswersWithGemini(correct_answer, student_answer, prompt)
            
        if(is_correct):
            # Correct answer
            continue_with_next = LLMAnswerChecker.updateRecord(student_id, example_id, date, duration, True, session_id=session_id)
            return (True, continue_with_next, "")
        else:
            # Incorrect answer
            continue_with_next = LLMAnswerChecker.updateRecord(student_id, example_id, date, duration, False, session_id=session_id)
            return (False, continue_with_next, "")