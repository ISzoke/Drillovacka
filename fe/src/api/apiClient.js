/**
 * ================================================================================
 * File: apiClient.js
 * Description:
 *       Axios client setup and API utility functions for interacting with the server.
 * Author: Dominik Horut (xhorut01)
 * ================================================================================
 */

import axios from 'axios';
import qs from 'qs';
import { getSessionId } from '@/utils/sessionManager';
import { i18n } from '@/i18n';
import { translateTaskNamesDeep } from '@/utils/contentNameMaps';

const currentLanguage = () => i18n.global.locale.value;

// Axios instance for all API requests
const apiClient = axios.create({
  baseURL: '/api/',
  headers: {
  },
});

/**
 * Helper: Get user identifier (student_id or session_id)
 * @param {number|null} studentId - Student ID if logged in, null otherwise
 * @returns {Object} { student_id: number|null, session_id: string|null }
 */
function getUserIdentifier(studentId) {
  if (studentId && studentId !== 0) {
    return { student_id: studentId, session_id: null };
  } else {
    return { student_id: null, session_id: getSessionId() };
  }
}

/**
 * Creates a new record indicating that a student has practiced a example.
 * 
 * @param {number} studentId - id of the student (0 for anonymous).
 * @param {number} exampleId - id of the example.
 * @param {Array<number>} practicedSkills - IDs of skills being practiced in this session.
 * @returns {string} timestamp of record.
 */
export const createRecord = async (studentId, exampleId, practicedSkills = [], practiceSessionKey = null) => {
    try {
      const userIdentifier = getUserIdentifier(studentId);
      const body = {
        ...userIdentifier,
        example_id: exampleId,
        practiced_skills: practicedSkills,
      };
      if (practiceSessionKey) body.practice_session_key = practiceSessionKey;
      const response = await apiClient.post('create-record/', body);
      return response.data;
    } catch (error) {
      throw error.response?.data?.error || 'Error creating record.';
    }
};

/**
 * Deletes a record that student practiced example.
 * 
 * @param {number} studentId - id of the student (0 for anonymous).
 * @param {number} exampleId - id of the example.
 * @param {string} date - timestamp of record creation.
 */
export const deleteRecord = async (studentId, exampleId, date) => {
  try {
    const userIdentifier = getUserIdentifier(studentId);
    await apiClient.post('delete-record/', {
      ...userIdentifier,
      example_id: exampleId,
      date
    });
  } catch (error) {
    throw error.response?.data?.error || 'Error updating record.';
  }
};

/**
 * Marks an example as skipped in record.
 * 
 * @param {number} studentId - id of the student (0 for anonymous).
 * @param {number} exampleId - id of the example.
 * @param {string} date - timestamp of record creation.
 */
export const skipExample = async (studentId, exampleId, date) => {
  try {
    const userIdentifier = getUserIdentifier(studentId);
    await apiClient.post('skip-example/', {
      ...userIdentifier,
      example_id: exampleId,
      date,
    });

  }catch (error) {
      throw error.response?.data?.error || 'Error skipping example.';
    }
};

/**
 * Creates or updates a task along with its associated examples.
 * 
 * @param {Array<Object>} examples - list of examples.
 * @param {Array<Object>} selectedSkills - list of selected skills.
 * @param {string} taskName - name of the task.
 * @param {number} taskId - id of the task (null if creating a new one).
 * @param {string} taskForm - form of task examples (classic or word-problem).
 * @param {string} action action type ('create' or 'update').
 */
export const postTask = async (examples, gradeLevelIds, taskName, taskId, taskForm, action) => {
  try {
      const payload = {
          task_name: taskName,
          task_id: taskId,
          task_form: taskForm,
          grade_level_ids: gradeLevelIds || [],
          examples: examples.value.map(example => ({
              example: example.example,
              example_id: example.example_id,
              answer: example.answer,
              input_type: example.input_type,
              steps: example.steps,
          }))
      };

      await apiClient.post(`${action}-task/`, payload);

  } catch (error) {
      if (error.response) {
          console.error('Error adding examples:', error.response.data);
      } else {
          console.error('Network or server error:', error.message);
      }
      throw error;
  }
};

/**
 * Gets skill data by its id.
 * 
 * @param {number} id - id of the skill.
 * @returns {Promise<Object>} skill data.
 */
export const getSkill = async (id) => {
  try {
    const response = await apiClient.get(`skill/${id}/`);
    return response.data;
    
  } catch (error) {
    console.error("Error fetching skill:", error)
  }
};

/**
 * Fetches a list of examples based on the provided skill ids.
 * 
 * @param {Array<string|number>} topics - array of skill or topic identifiers.
 * @returns {Promise<Array<Object>>} list of example objects.
 */
export const getExamples = async (topics) => {
  try {
    const response = await apiClient.get('examples/', {
      params: {
        topics: JSON.stringify(topics),
      },
      paramsSerializer: (params) => {
        return qs.stringify(params, { arrayFormat: 'repeat' });
      },
    });

    return response.data;

  } catch (error) {
    console.error("Error fetching examples:", error);
  }
};

/**
 * Fetches all examples for a specific task.
 *
 * @param {number} taskId - id of the task.
 * @returns {Promise<Array<Object>>}
 */
export const getTaskExamples = async (taskId) => {
  try {
    const response = await apiClient.get('examples/', {
      params: {
        task_id: taskId,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching task examples:', error);
    return [];
  }
};

export const revealAnswer = async (exampleId) => {
  try {
    const response = await apiClient.get(`examples/${exampleId}/answer/`);
    return response.data.answer;
  } catch (error) {
    console.error('Error revealing answer:', error);
    return '';
  }
};

/**
 * Retrieves all tasks.
 * 
 * @returns {Promise<Array<Object>>} array of task objects.
 */
export const getTasks = async () => {
  try {
    const response = await apiClient.get('tasks/');
    return response.data;

  } catch (error) {
    console.error("Error fetching skills:", error)
  }
};

export const getTask = async (taskId) => {
  const response = await apiClient.get(`tasks/${taskId}/`);
  return response.data;
};

export const getTaskStats = async (taskId, studentId = null) => {
  const userIdentifier = getUserIdentifier(studentId);
  const params = userIdentifier.student_id
    ? { student_id: userIdentifier.student_id }
    : { session_id: userIdentifier.session_id };
  const response = await apiClient.get(`tasks/${taskId}/stats/`, { params });
  return response.data;
};

export const getTaskHistory = async (taskId, studentId = null) => {
  const userIdentifier = getUserIdentifier(studentId);
  const params = userIdentifier.student_id
    ? { student_id: userIdentifier.student_id }
    : { session_id: userIdentifier.session_id };
  const response = await apiClient.get(`tasks/${taskId}/history/`, { params });
  return response.data.history;
};

/**
 * Retrieves compact task data for grade assignment admin.
 *
 * @returns {Promise<Array<Object>>} array of summarized task objects.
 */
export const getTaskAssignmentOverview = async () => {
  try {
    const response = await apiClient.get('tasks/assignment-overview/');
    return response.data;
  } catch (error) {
    console.error('Error fetching task assignment overview:', error);
    return [];
  }
};

/**
 * Deletes an example by its id.
 * 
 * @param {number} exampleId - id of the example.
 */
export const deleteExample = async (exampleId) => {
  try {
    await apiClient.delete(`example/${exampleId}/delete/`);

  } catch (error) {
    throw error.response?.data?.error || 'Error deleting example.';
  }
};

/**
 * Deletes a task and its associated examples.
 * 
 * @param {number} taskId - id of the task.
 */
export const deleteTask = async (taskId) => {
  try {
    await apiClient.delete(`tasks/${taskId}/delete/`);

  } catch (error) {
    console.error('Error deleting task:', error);
  }
};

/**
 * Updates the grade levels assigned to a task.
 *
 * @param {number} taskId - id of the task.
 * @param {Array<number>} gradeLevelIds - array of grade level ids to assign.
 * @returns {Promise<Object>} updated task grade data
 */
export const updateTaskGradeLevels = async (taskId, gradeLevelIds) => {
  try {
    const response = await apiClient.patch(`tasks/${taskId}/grade-levels/`, {
      grade_levels: gradeLevelIds,
    });
    return response.data;
  } catch (error) {
    console.error('Error updating task grade levels:', error);
    throw error.response?.data?.error || 'Error updating task grade levels.';
  }
};

/**
 * Creates a new skill or recreates a previously soft-deleted one.
 * 
 * @param {string} name - name of the skill to be created.
 * @param {number} [parent_id=null] - id of the parent skill, if any.
 * @returns {Promise<Object>} created skill data.
 */
export const createSkill = async (name, parent_id = null) => {
  try {
    const response = await apiClient.post('create-skill/', {
      name,
      parent_skill: parent_id, 
    });

    return response.data; 

  } catch (error) {
    throw error.response?.data?.error || 'Error creating skill.';
  }
};

/**
 * Retrieves the full skill tree.
 * 
 * @returns {Promise<Array<Object>>} array representing the skill tree structure.
 */
export const getSkillTree = async () => {
  try {
    const response = await apiClient.get('skill-tree/');

    return response.data;

  } catch (error) {
    console.error('Error fetching skill tree:', error);
  }
};

/**
 * Searches for child skills based on a query and a parent skill ID.
 * 
 * @param {string} query - search keyword to filter skills.
 * @param {number} skillId - id of the parent skill.
 * @returns {Promise<Array<Object>>} list of matching skills.
 */
export const searchSkills = async (query, skillId) => {
  console.log(typeof(skillId))
  try {
    const response = await apiClient.get('skills/search/', {
      params: {
        q: query,
        skill_id: skillId
      }
    });

    return response.data;

  } catch (error) {
    console.error('Error fetching search results:', error);
    return [];
  }
};

/**
 * Retrieves a list of skills to be shown on the landing page.
 * 
 * @returns {Promise<Array<Object>>} - array of landing page skills.
 */
export const getLandingPageSkills = async () => {
  try {
    const response = await apiClient.get('landing-page-skills/');

    return response.data;

  } catch (error) {
    console.error('Error fetching landing page skills:', error);
  }
};

/**
 * Retrieves the related skills tree for a given skill id.
 * 
 * @param {number} skillId - id of the skill to fetch related skills for.
 * @returns {Promise<Object>} related skills tree.
 */
export const getRelatedSkillsTree = async (skillId) => {
  try {
    const response = await apiClient.get(`skills/${skillId}/tree/related`);

    return response.data;

  } catch (error) {
    console.error('Error fetching related skills:', error);
  }
};

/**
 * Retrieves the children skills tree for a given skill ID.
 * 
 * @param {number} skillId - id of the parent skill.
 * @param {boolean} withCounts whether to include counts of examples.
 * @returns {Promise<Object>} children skills tree.
 */
export const getChildrenSkillsTree = async (skillId, withCounts) => {
  try {
    const response = await apiClient.get(`skills/${skillId}/tree/children`,{
      params: {
        with_counts: withCounts,
      }
    });

    return response.data;

  } catch (error) {
    console.error('Error fetching related skills:', error);
  }
};

/**
 * Retrieves operation skills associated with a specific skill ID.
 * 
 * @param {number} skillId - id of the skill to fetch operation skills for.
 * @returns {Promise<Array<Object>>} list of operation skills.
 */
export const getOperationSkills = async (skillId) => {
  try {
    const response = await apiClient.get(`skills/${skillId}/operations`);

    return response.data;

  } catch (error) {
    console.error('Error fetching operation skills:', error);
  }
};

/**
 * Soft-deletes a skill by its id.
 * 
 * @param {number} skillId - id of the skill to be deleted.
 */
export const deleteSkill = async (skillId) => {
  try {
    await apiClient.patch(`skills/${skillId}/delete/`);

  } catch (error) {
    throw error.response?.data?.error || 'Error deleting skill';
  }
};

/**
 * Registers a new user with the provided username and passphrase.
 * 
 * @param {string} username - username for the new user.
 * @param {string} passphrase - passphrase for the new user.
 * @returns {Promise<Object>} server response..
 */
export const registerStudent = async (username, passphrase, grade = null) => {
  try {
    const response = await apiClient.post('/register/student', {
      username,
      passphrase,
      ...(grade !== null ? { grade } : {}),
    });

    return response;

  } catch (error) {

    if (error.response && error.response.data) {
      return { error: error.response.data.error };
    }
  }
};

/**
 * Logs in a user using the provided credentials.
 * 
 * @param {string} username - users username.
 * @param {string} passphrase - users passphrase.
 * @returns {Promise<Object>} server response.
 */
export const loginStudent = async (username, passphrase) => {
  try {
    const response = await apiClient.post('/login/student', {
      username,
      passphrase
    });

    return response;

  } catch (error) {
    if (error.response && error.response.data) {
      return { error: error.response.data.error };
    }
  }
};

/**
 * Updates the grade of a student (allowed once after registration).
 *
 * @param {number} studentId
 * @param {number} grade - 1 to 9
 * @returns {Promise<Object>} updated grade data
 */
export const updateStudentGrade = async (studentId, grade) => {
  try {
    const response = await apiClient.patch(`/student/${studentId}/grade/`, { grade });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error updating grade';
  }
};

/**
 * Logs in an admin using the provided credentials.
 *
 * @param {string} username - The admin's username.
 * @param {string} password - The admin's password.
 * @returns {Promise<Object>} the server.
 */
export const loginAdmin = async (username, password) => {
  try {
    const response = await apiClient.post('/login/admin', {
      username,
      password
    });

    return response;

  } catch (error) {
    if (error.response && error.response.data) {
      return { error: error.response.data.error };
    }
  }
};

/**
 * Checks user answer.
 * 
 * @param {number} student_id - id of the user (0 for anonymous).
 * @param {number} example_id - id of the example.
 * @param {string} date - timestamp of record.
 * @param {number} duration - elapsed time user practiced example.
 * @param {string} student_answer - users answer.
 * @param {string} answer_type - type of answer type ('inline', 'frac', 'var').
 * @returns {Promise<Object>} evaluation result from the server.
 */
export const checkAnswer = async (student_id, example_id, date, duration, student_answer, answer_type) => {
  try {
    const userIdentifier = getUserIdentifier(student_id);
    const response = await apiClient.post('check-answer/', {
      ...userIdentifier,
      example_id,
      date,
      duration,
      student_answer,
      answer_type
    });

    return response.data;

  } catch (error) {
    console.error('Error checking answer:', error);
  }
};

/**
 * Retrieves full skill paths for the given skill ids, returning the paths with entire skill data.
 * 
 * @param {Array<number>} skillIds - array of skill ids to retrieve paths for.
 * @returns {Promise<Object>} skill paths.
 */
export const getSandboxSkillPaths = async (skillIds) => {
  try {
    const response = await apiClient.get('skills/paths/sandbox/', {
      params: {
        skill_ids: skillIds
      },
      paramsSerializer: (params) => {
        return new URLSearchParams(params).toString();
      }
    });

    return response.data;

  } catch (error) {
    console.error('Error fetching sandbox skill paths:', error);
  }
};

/**
 * Retrieves the number of tasks and examples associated with a given skill id.
 * 
 * @param {number} skillId - id of the skill to fetch related task and example counts for.
 * @returns {Promise<Object>} counts of related tasks and examples.
 */
export const getRelatedTasksCount = async (skillId) => {
  try {
    const response = await apiClient.get('skills/related-counts/', {
      params: {
        skill_id: skillId
      }
    });

    return response.data;

  } catch (error) {
    console.error('Error fetching tasks and examples count:', error);
  }
};

/**
 * Submits an answer to a survey question, along with optional related skills.
 * 
 * @param {string} questionType - category of the survey question.
 * @param {string} questionText - text of the survey question.
 * @param {string} answer - users answer to the question.
 * @param {Array<number>} skills - array of skill ids which user was practicing.
 */
export const sendSurveyAnswer = async (questionType, questionText, answer, skills, studentId = null, sessionId = null, language = '') => {
  try {
    await apiClient.post('survey-answer/', {
      question_type: questionType,
      question_text: questionText,
      answer,
      skills,
      student_id: studentId,
      session_id: sessionId,
      language,
    });

  } catch (error) {
    console.error('Error sending survey answer:', error);
  }
};

/**
 * Sends an example report for a concrete practiced example.
 *
 * @param {Object} payload - report payload
 * @returns {Promise<Object>} server response
 */
export const sendExampleReport = async (payload) => {
  try {
    const response = await apiClient.post('example-report/', payload);
    return response.data;
  } catch (error) {
    console.error('Error sending example report:', error);
    throw error.response?.data?.error || 'Error sending example report.';
  }
};

/**
 * Fetches all available grade levels (1-9).
 * 
 * @returns {Promise<Array<Object>>} array of grade level objects with id and grade.
 */
export const getGradeLevels = async () => {
  try {
    const response = await apiClient.get('grade-levels/');
    return response.data;
  } catch (error) {
    console.error('Error fetching grade levels:', error);
    return [];
  }
};

/**
 * Fetches manually assigned tasks for a specific grade.
 *
 * @param {number} gradeId - id of the grade level.
 * @returns {Promise<Array<Object>>}
 */
export const getTasksByGrade = async (gradeId, studentId = null) => {
  try {
    const params = studentId ? { student_id: studentId } : {};
    const response = await apiClient.get(`tasks/by-grade/${gradeId}/`, { params });
    return translateTaskNamesDeep(response.data, currentLanguage());
  } catch (error) {
    console.error('Error fetching tasks by grade:', error);
    return [];
  }
};

/**
 * Updates the grade levels assigned to a skill.
 * 
 * @param {number} skillId - id of the skill to update.
 * @param {Array<number>} gradeLevelIds - array of grade level ids to assign.
 * @returns {Promise<Object>} updated skill data.
 */
export const updateSkillGradeLevels = async (skillId, gradeLevelIds) => {
  try {
    const response = await apiClient.patch(`skills/${skillId}/grade-levels/`, {
      grade_levels: gradeLevelIds
    });
    return response.data;
  } catch (error) {
    console.error('Error updating skill grade levels:', error);
    throw error;
  }
};

/**
 * Fetches skill analytics for a student (mastery, accuracy, etc.)
 * @param {number|string} studentId
 * @returns {Promise<Array>} Array of skill stats
 */
export const getStudentSkillStats = async (studentId) => {
  try {
    const response = await apiClient.get(`analytics/student/${studentId}/skills/`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching skill analytics.';
  }
};

/**
 * Fetches student skill analytics grouped by skill combinations (not individual skills)
 * @param {number} studentId - ID of the student
 * @returns {Promise<Array>} Array of skill combinations with stats
 */
export const getStudentSkillCombinations = async (studentId) => {
  try {
    const response = await apiClient.get(`analytics/student/${studentId}/skill-combinations/`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching skill combinations.';
  }
};

/**
 * Fetches list of all students with their overall stats
 * @returns {Promise<Array>} Array of students with stats
 */
export const getAllStudentsStats = async () => {
  try {
    const response = await apiClient.get('analytics/students/');
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching students list.';
  }
};

/**
 * Fetches list of anonymous sessions with aggregated stats
 * @returns {Promise<Array>} Array of anonymous sessions
 */
export const getAllAnonymousSessionsStats = async () => {
  try {
    const response = await apiClient.get('analytics/anonymous-sessions/');
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching anonymous sessions list.';
  }
};

/**
 * Fetches complete stored personal data (attempt logs + summary)
 * @param {Object} params - { student_id } or { session_id }
 * @returns {Promise<Object>} user data payload
 */
export const getMyData = async (params) => {
  try {
    const response = await apiClient.get('my-data/', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching my data.';
  }
};

/**
 * Fetches reported examples for admin overview.
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export const getExampleReports = async (limit = 500) => {
  try {
    const response = await apiClient.get('example-reports/', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching example reports.';
  }
};

export const getAllExampleRequests = async (limit = 500) => {
  try {
    const response = await apiClient.get('example-requests/all/', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching example requests.';
  }
};

/**
 * Fetches stored survey/final feedback entries for admin overview.
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export const getSurveyFeedbacks = async (limit = 500) => {
  try {
    const response = await apiClient.get('survey-feedbacks/', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error fetching survey feedbacks.';
  }
};

/**
 * Initialize or get anonymous session
 * @param {string} sessionId - Optional existing session ID
 * @returns {Promise<Object>} Session data with session_id, language, created
 */
export const initSession = async (sessionId = null) => {
  try {
    const response = await apiClient.post('session/init/', {
      session_id: sessionId
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error initializing session.';
  }
};

/**
 * Update language preference for anonymous session
 * @param {string} sessionId - Session ID
 * @param {string} language - Language code (cs/sk/en)
 * @returns {Promise<Object>} Updated session data
 */
export const updateSessionLanguage = async (sessionId, language) => {
  try {
    const response = await apiClient.post('session/update-language/', {
      session_id: sessionId,
      language: language
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error updating language.';
  }
};

/**
 * Update language preference for authenticated student
 * @param {number} studentId - Student ID
 * @param {string} language - Language code (cs/sk/en)
 * @returns {Promise<Object>} Updated student data
 */
export const updateStudentLanguage = async (studentId, language) => {
  try {
    const response = await apiClient.post('student/update-language/', {
      student_id: studentId,
      language: language
    });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error updating language.';
  }
};

/**
 * Bulk import tasks with examples.
 * @param {Array<Object>} tasks - Array of task objects
 * @returns {Promise<Object>} Import results
 */
export const bulkImportTasks = async (tasks) => {
  try {
    const response = await apiClient.post('bulk-import-tasks/', { tasks });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error importing tasks.';
  }
};

/**
 * Export attempts as CSV (DKT-ready).
 * @param {Object} params - Query params (student_id, session_id, all_actions, date_from, date_to)
 * @returns {Promise<string>} CSV download URL
 */
export const getExportCsvUrl = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return `/api/export/csv/${query ? '?' + query : ''}`;
};

// ── AI Example Generation ────────────────────────────────────────────────────

export const getGenerationQuota = async (studentId) => {
  const response = await apiClient.get('generation-quota/', { params: { student_id: studentId } });
  return response.data; // { used, limit, remaining }
};

export const generateExamples = async (payload) => {
  try {
    const response = await apiClient.post('generate-examples/', payload);
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error generating examples.';
  }
};

export const submitGeneratedBatchSurvey = async (batchId, answers) => {
  try {
    const response = await apiClient.post(`generated-batches/${batchId}/survey/`, answers);
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error submitting survey.';
  }
};

export const getMyGeneratedBatches = async (params = {}) => {
  try {
    const response = await apiClient.get('my-generated-batches/', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error loading generated batches.';
  }
};

export const getAllGeneratedBatches = async (params = {}) => {
  try {
    const response = await apiClient.get('generated-batches/', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error loading generated batches.';
  }
};

export const approveGeneratedBatch = async (batchId) => {
  try {
    const response = await apiClient.post(`generated-batches/${batchId}/approve/`);
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error approving batch.';
  }
};

export const rejectGeneratedBatch = async (batchId, note = '') => {
  try {
    const response = await apiClient.post(`generated-batches/${batchId}/reject/`, { note });
    return response.data;
  } catch (error) {
    throw error.response?.data?.error || 'Error rejecting batch.';
  }
};

export const deleteGeneratedBatch = async (batchId, studentId) => {
  try {
    await apiClient.delete(`generated-batches/${batchId}/delete/`, { params: { student_id: studentId } });
  } catch (error) {
    throw error.response?.data?.error || 'Error deleting batch.';
  }
};

// ── Teacher Auth ────────────────────────────────────────────────────────────

export const registerTeacher = async (email, password, firstName, lastName) => {
  try {
    const response = await apiClient.post('/register/teacher', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    return response;
  } catch (error) {
    if (error.response && error.response.data) {
      return { error: error.response.data.error };
    }
  }
};

export const loginTeacher = async (email, password) => {
  try {
    const response = await apiClient.post('/login/teacher', {
      email,
      password,
    });
    return response;
  } catch (error) {
    if (error.response && error.response.data) {
      return { error: error.response.data.error };
    }
  }
};

// ── Classrooms ──────────────────────────────────────────────────────────────

export const getTeacherClassrooms = async (teacherId) => {
  const response = await apiClient.get('classrooms/', { params: { teacher_id: teacherId } });
  return response.data;
};

export const createClassroom = async (teacherId, name, description = '') => {
  const response = await apiClient.post('classrooms/', {
    teacher_id: teacherId,
    name,
    description,
  });
  return response.data;
};

export const getClassroomDetail = async (classroomId, { teacherId, studentId } = {}) => {
  const params = {};
  if (teacherId) params.teacher_id = teacherId;
  if (studentId) params.student_id = studentId;
  const response = await apiClient.get(`classrooms/${classroomId}/`, { params });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const updateClassroom = async (classroomId, teacherId, data) => {
  const response = await apiClient.patch(`classrooms/${classroomId}/`, {
    teacher_id: teacherId,
    ...data,
  });
  return response.data;
};

export const deleteClassroom = async (classroomId, teacherId) => {
  await apiClient.delete(`classrooms/${classroomId}/`, {
    params: { teacher_id: teacherId },
  });
};

// ── Student Classroom Join ──────────────────────────────────────────────────

export const joinClassroom = async (studentId, code) => {
  const response = await apiClient.post('classrooms/join/', {
    student_id: studentId,
    code,
  });
  return response.data;
};

export const getStudentClassrooms = async (studentId) => {
  const response = await apiClient.get('classrooms/student/', {
    params: { student_id: studentId },
  });
  return response.data;
};

export const leaveClassroom = async (classroomId, studentId) => {
  await apiClient.delete(`classrooms/${classroomId}/leave/`, {
    data: { student_id: studentId },
  });
};

export const getClassroomByCode = async (code) => {
  const response = await apiClient.get('classrooms/info/', { params: { code } });
  return response.data;
};

// ── Classroom Tasks ─────────────────────────────────────────────────────────

export const getClassroomTasks = async (classroomId, { teacherId, studentId } = {}) => {
  const params = {};
  if (teacherId) params.teacher_id = teacherId;
  if (studentId) params.student_id = studentId;
  const response = await apiClient.get(`classrooms/${classroomId}/tasks/`, { params });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const assignTaskToClassroom = async (classroomId, teacherId, taskId, isHomework = false, dueDate = null) => {
  const response = await apiClient.post(`classrooms/${classroomId}/tasks/`, {
    teacher_id: teacherId,
    task_id: taskId,
    is_homework: isHomework,
    due_date: dueDate,
  });
  return response.data;
};

export const removeTaskFromClassroom = async (classroomId, taskId, teacherId) => {
  await apiClient.delete(`classrooms/${classroomId}/tasks/${taskId}/`, {
    data: { teacher_id: teacherId },
  });
};

export const updateClassroomTask = async (classroomId, taskId, teacherId, data) => {
  const response = await apiClient.patch(`classrooms/${classroomId}/tasks/${taskId}/`, {
    teacher_id: teacherId,
    ...data,
  });
  return response.data;
};

export const removeStudentFromClassroom = async (classroomId, teacherId, studentId) => {
  await apiClient.post(`classrooms/${classroomId}/remove-student/`, {
    teacher_id: teacherId,
    student_id: studentId,
  });
};

// ── Classroom Analytics ─────────────────────────────────────────────────────

export const getClassroomAnalytics = async (classroomId, teacherId) => {
  const response = await apiClient.get(`classrooms/${classroomId}/analytics/`, {
    params: { teacher_id: teacherId },
  });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const getClassroomStudentDetail = async (classroomId, studentId, teacherId) => {
  const response = await apiClient.get(`classrooms/${classroomId}/students/${studentId}/`, {
    params: { teacher_id: teacherId },
  });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const getClassroomTaskHomeworkStats = async (classroomId, taskId, teacherId) => {
  const response = await apiClient.get(`classrooms/${classroomId}/tasks/${taskId}/homework-stats/`, {
    params: { teacher_id: teacherId },
  });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const teacherGenerateTaskPreview = async (teacherId, type, count, description, segments = null) => {
  const response = await apiClient.post('teacher/generate-task/', {
    teacher_id: teacherId, type, count, description, language: currentLanguage(),
    ...(segments && { segments }),
  });
  return response.data;
};

export const teacherSaveTask = async (teacherId, taskName, form, grade, examples, generationPrompt = '', generationParams = null) => {
  const response = await apiClient.post('teacher/save-task/', {
    teacher_id: teacherId, task_name: taskName, form, grade, examples,
    generation_prompt: generationPrompt,
    generation_params: generationParams,
  });
  return response.data;
};

// ── Teacher Example Library ─────────────────────────────────────────────────

export const teacherListExamples = async (teacherId, { search = '', unattachedOnly = false, grade = null, taskId = null } = {}) => {
  const params = { teacher_id: teacherId };
  if (search) params.search = search;
  if (unattachedOnly) params.unattached_only = 1;
  if (grade) params.grade = grade;
  if (taskId) params.task_id = taskId;
  const response = await apiClient.get('teacher/examples/', { params });
  return response.data;
};

export const getUnassignedExampleCount = async (teacherId) => {
  const response = await apiClient.get('teacher/examples/unassigned-count/', { params: { teacher_id: teacherId } });
  return response.data;
};

export const teacherBulkSetGrade = async (teacherId, exampleIds, grade) => {
  const response = await apiClient.post('teacher/examples/bulk-set-grade/', {
    teacher_id: teacherId, example_ids: exampleIds, grade,
  });
  return response.data;
};

export const teacherBulkDelete = async (teacherId, exampleIds) => {
  const response = await apiClient.post('teacher/examples/bulk-delete/', {
    teacher_id: teacherId, example_ids: exampleIds,
  });
  return response.data;
};

export const teacherBulkAddToTask = async (teacherId, exampleIds, taskId) => {
  const response = await apiClient.post('teacher/examples/bulk-add-to-task/', {
    teacher_id: teacherId, example_ids: exampleIds, task_id: taskId,
  });
  return response.data;
};

export const teacherBulkCreateTask = async (teacherId, exampleIds, taskName) => {
  const response = await apiClient.post('teacher/examples/bulk-create-task/', {
    teacher_id: teacherId, example_ids: exampleIds, task_name: taskName,
  });
  return response.data;
};

export const teacherCreateExample = async (teacherId, { example, inputType, answer, steps = [], grade = null }) => {
  const response = await apiClient.post('teacher/examples/', {
    teacher_id: teacherId, example, input_type: inputType, answer, steps, grade,
  });
  return response.data;
};

export const teacherUpdateExample = async (exampleId, teacherId, { example, inputType, answer, steps, grade }) => {
  const response = await apiClient.patch(`teacher/examples/${exampleId}/`, {
    teacher_id: teacherId, example, input_type: inputType, answer, steps, grade,
  });
  return response.data;
};

export const teacherPrintTest = async (teacherId, payload) => {
  const response = await apiClient.post('teacher/print/test/', {
    teacher_id: teacherId, ...payload,
  }, { responseType: 'blob' });
  return response.data;
};

export const getMyTeacherTasks = async (teacherId) => {
  const response = await apiClient.get('teacher/tasks/mine/', { params: { teacher_id: teacherId } });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const teacherDeleteExample = async (exampleId, teacherId) => {
  await apiClient.delete(`teacher/examples/${exampleId}/`, { data: { teacher_id: teacherId } });
};

export const getTeacherTaskExamples = async (taskId, teacherId) => {
  const response = await apiClient.get(`teacher/tasks/${taskId}/examples/`, {
    params: { teacher_id: teacherId },
  });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const teacherGenerateMoreExamplesPreview = async (teacherId, taskId, description, count) => {
  const response = await apiClient.post(`teacher/tasks/${taskId}/generate-more/`, {
    teacher_id: teacherId, description, count, language: currentLanguage(),
  });
  return response.data;
};

export const teacherSaveGeneratedExamples = async (teacherId, taskId, examples, description = '') => {
  const response = await apiClient.post(`teacher/tasks/${taskId}/generate-more/save/`, {
    teacher_id: teacherId, examples, description,
  });
  return response.data;
};

export const attachExampleToTask = async (taskId, teacherId, exampleId) => {
  const response = await apiClient.post(`teacher/tasks/${taskId}/examples/attach/`, {
    teacher_id: teacherId, example_id: exampleId,
  });
  return response.data;
};

export const detachExampleFromTask = async (taskId, teacherId, exampleId) => {
  await apiClient.post(`teacher/tasks/${taskId}/examples/detach/`, {
    teacher_id: teacherId, example_id: exampleId,
  });
};

export const copyExampleIntoTask = async (taskId, teacherId, sourceExampleId) => {
  const response = await apiClient.post(`teacher/tasks/${taskId}/examples/copy-in/`, {
    teacher_id: teacherId, source_example_id: sourceExampleId,
  });
  return response.data;
};

export const copyTaskForTeacher = async (teacherId, sourceTaskId, newName = '') => {
  const response = await apiClient.post('teacher/tasks/copy/', {
    teacher_id: teacherId, source_task_id: sourceTaskId, new_name: newName,
  });
  return response.data;
};

export const deleteTeacherTask = async (taskId, teacherId) => {
  await apiClient.delete(`teacher/tasks/${taskId}/delete/`, { data: { teacher_id: teacherId } });
};

// ── Task Browsing ───────────────────────────────────────────────────────────

export const browseTasks = async (grade = null, search = '') => {
  const params = {};
  if (grade) params.grade = grade;
  if (search) params.search = search;
  const response = await apiClient.get('tasks/browse/', { params });
  return translateTaskNamesDeep(response.data, currentLanguage());
};

export const getRecentActivity = async (limit = 100) => {
  const response = await apiClient.get('analytics/activity/', { params: { limit } });
  return response.data;
};

export const getAllTeachers = async () => {
  const response = await apiClient.get('admin/teachers/');
  return response.data;
};

export const getAdminClassroomStudents = async (classroomId) => {
  const response = await apiClient.get(`admin/classrooms/${classroomId}/students/`);
  return response.data;
};

export const getAdminTaskExamples = async (taskId) => {
  const response = await apiClient.get(`admin/tasks/${taskId}/examples/`);
  return response.data;
};

export const publishTeacherTask = async (taskId, gradeIds) => {
  const response = await apiClient.post(`admin/tasks/${taskId}/publish/`, { grade_ids: gradeIds });
  return response.data;
};

// ── Duel (preťahovanie lanom) ───────────────────────────────────────────────

export const createDuel = async (studentId, { mode, visibility, taskId, timeLimitSeconds, vsBot, botDifficulty, displayName }) => {
  const userIdentifier = getUserIdentifier(studentId);
  const response = await apiClient.post('duel/create/', {
    ...userIdentifier,
    mode,
    visibility,
    task_id: taskId,
    time_limit_seconds: timeLimitSeconds,
    vs_bot: vsBot || false,
    bot_difficulty: botDifficulty,
    display_name: displayName,
  });
  return response.data;
};

export const joinDuel = async (studentId, code, displayName) => {
  const userIdentifier = getUserIdentifier(studentId);
  const response = await apiClient.post('duel/join/', { ...userIdentifier, code, display_name: displayName });
  return response.data;
};

export const listPublicDuels = async () => {
  const response = await apiClient.get('duel/public/');
  return response.data;
};

export const getDuelState = async (code) => {
  const response = await apiClient.get(`duel/state/${code}/`);
  return response.data;
};

// ── Live kvíz (Kahoot-style) ────────────────────────────────────────────────

export const createQuiz = async (teacherId, taskId) => {
  const response = await apiClient.post('quiz/create/', { teacher_id: teacherId, task_id: taskId });
  return response.data;
};

export const joinQuiz = async (studentId, code, displayName) => {
  const userIdentifier = getUserIdentifier(studentId);
  const response = await apiClient.post('quiz/join/', { ...userIdentifier, code, display_name: displayName });
  return response.data;
};

export const getQuizState = async (code) => {
  const response = await apiClient.get(`quiz/state/${code}/`);
  return response.data;
};

export default apiClient;
