<template>
  <div class="p-6 max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">{{ t('myDataPageTitle') }}</h1>

    <div class="border rounded-lg p-4 mb-6">
      <div class="flex items-center justify-between gap-4 mb-3">
        <h2 class="text-lg font-semibold">{{ t('reportedExamplesTitle') }}</h2>
        <button
          @click="loadReports"
          class="bg-amber-500 text-white px-4 py-2 rounded"
        >
          {{ t('refreshReports') }}
        </button>
      </div>

      <div v-if="reportsLoading" class="text-gray-500">{{ t('loadingReports') }}</div>
      <div v-else-if="reportsError" class="text-red-600">{{ reportsError }}</div>
      <div v-else-if="exampleReports.length === 0" class="text-gray-500">{{ t('noReportsYet') }}</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">{{ t('colTime') }}</th>
              <th class="p-2 border">{{ t('colUser') }}</th>
              <th class="p-2 border">{{ t('colReason') }}</th>
              <th class="p-2 border">{{ t('colNote') }}</th>
              <th class="p-2 border">{{ t('colTask') }}</th>
              <th class="p-2 border">{{ t('colExample') }}</th>
              <th class="p-2 border">{{ t('correctAnswer') }}</th>
              <th class="p-2 border">{{ t('colInputType') }}</th>
              <th class="p-2 border">{{ t('colLanguage') }}</th>
              <th class="p-2 border">{{ t('skills') }}</th>
              <th class="p-2 border">{{ t('colMegaMeta') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in exampleReports" :key="report.report_id">
              <td class="p-2 border whitespace-nowrap">{{ formatDate(report.created_at) }}</td>
              <td class="p-2 border">
                <div v-if="report.student_id">
                  <div class="font-semibold">{{ report.student_username || t('studentFallbackName') }}</div>
                  <div class="text-xs text-gray-600">ID: {{ report.student_id }}</div>
                </div>
                <div v-else>
                  <div class="font-semibold">{{ t('anonymousUserLabel') }}</div>
                  <div class="text-xs text-gray-600 break-all">{{ report.anonymous_session_id || '-' }}</div>
                </div>
              </td>
              <td class="p-2 border">{{ formatReportType(report.report_type) }}</td>
              <td class="p-2 border">{{ report.note || '-' }}</td>
              <td class="p-2 border">
                <div class="font-semibold">{{ report.task_name || '-' }}</div>
                <div class="text-xs text-gray-600">{{ t('exampleIdLabel') }} {{ report.example_id }}</div>
              </td>
              <td class="p-2 border">{{ report.example_text }}</td>
              <td class="p-2 border">{{ report.correct_answer || '-' }}</td>
              <td class="p-2 border text-center">{{ report.input_type || '-' }}</td>
              <td class="p-2 border text-center">{{ report.language || '-' }}</td>
              <td class="p-2 border">{{ (report.practiced_skill_names || []).join(', ') || '-' }}</td>
              <td class="p-2 border min-w-56">
                <div class="text-xs space-y-2">
                  <div>
                    <span class="font-semibold">{{ t('uploadedLabel') }}</span>
                    <span :class="report.mega_uploaded ? 'text-green-700' : 'text-gray-600'">
                      {{ report.mega_uploaded ? t('yesLabel') : t('noLabel') }}
                    </span>
                  </div>
                  <div v-if="report.mega_json_url">
                    <a
                      :href="report.mega_json_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 underline break-all"
                    >
                      {{ t('jsonOnMega') }}
                    </a>
                  </div>
                  <div v-else class="text-gray-500">{{ t('megaLinkNone') }}</div>
                  <div class="break-all text-gray-600">{{ report.local_json_name || '' }}</div>
                  <div v-if="report.mega_error" class="text-red-600 break-all">{{ report.mega_error }}</div>
                  <details class="mt-2">
                    <summary class="cursor-pointer text-gray-700">{{ t('rawMetaLabel') }}</summary>
                    <pre class="mt-2 whitespace-pre-wrap break-all text-[11px] text-gray-600">{{ JSON.stringify(report.meta || {}, null, 2) }}</pre>
                  </details>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="border rounded-lg p-4 mb-6">
      <div class="flex items-center justify-between gap-4 mb-3">
        <h2 class="text-lg font-semibold">{{ t('feedbackSurveysTitle') }}</h2>
        <button
          @click="loadSurveyFeedbacks"
          class="bg-emerald-600 text-white px-4 py-2 rounded"
        >
          {{ t('refreshFeedbacks') }}
        </button>
      </div>

      <div v-if="feedbacksLoading" class="text-gray-500">{{ t('loadingFeedbacks') }}</div>
      <div v-else-if="feedbacksError" class="text-red-600">{{ feedbacksError }}</div>
      <div v-else-if="surveyFeedbacks.length === 0" class="text-gray-500">{{ t('noFeedbacksYet') }}</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">{{ t('colTime') }}</th>
              <th class="p-2 border">{{ t('colUser') }}</th>
              <th class="p-2 border">{{ t('colType') }}</th>
              <th class="p-2 border">{{ t('colSource') }}</th>
              <th class="p-2 border">{{ t('colQuestion') }}</th>
              <th class="p-2 border">{{ t('colAnswer') }}</th>
              <th class="p-2 border">{{ t('colLanguage') }}</th>
              <th class="p-2 border">{{ t('skills') }}</th>
              <th class="p-2 border">{{ t('colAudioMega') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="feedback in surveyFeedbacks" :key="feedback.feedback_id">
              <td class="p-2 border whitespace-nowrap">{{ formatDate(feedback.created_at) }}</td>
              <td class="p-2 border">
                <div v-if="feedback.student_id">
                  <div class="font-semibold">{{ feedback.student_username || t('studentFallbackName') }}</div>
                  <div class="text-xs text-gray-600">ID: {{ feedback.student_id }}</div>
                </div>
                <div v-else>
                  <div class="font-semibold">{{ t('anonymousUserLabel') }}</div>
                  <div class="text-xs text-gray-600 break-all">{{ feedback.anonymous_session_id || '-' }}</div>
                </div>
              </td>
              <td class="p-2 border">{{ formatFeedbackType(feedback.question_type) }}</td>
              <td class="p-2 border text-center">{{ feedback.source || '-' }}</td>
              <td class="p-2 border">{{ feedback.question_text || '-' }}</td>
              <td class="p-2 border">{{ feedback.answer || '-' }}</td>
              <td class="p-2 border text-center">{{ feedback.language || '-' }}</td>
              <td class="p-2 border">{{ (feedback.practiced_skill_names || []).join(', ') || '-' }}</td>
              <td class="p-2 border min-w-56">
                <div class="space-y-2 text-xs">
                  <audio
                    v-if="feedback.audio_url"
                    :src="feedback.audio_url"
                    controls
                    preload="none"
                    class="w-full"
                  />
                  <div v-else class="text-gray-500">{{ t('audioNone') }}</div>
                  <div>
                    <span class="font-semibold">{{ t('uploadedLabel') }}</span>
                    <span :class="feedback.mega_uploaded ? 'text-green-700' : 'text-gray-600'">
                      {{ feedback.mega_uploaded ? t('yesLabel') : t('noLabel') }}
                    </span>
                  </div>
                  <div v-if="feedback.mega_json_url" class="break-all">
                    <a
                      :href="feedback.mega_json_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 underline"
                    >
                      {{ t('jsonOnMega') }}
                    </a>
                  </div>
                  <div v-if="feedback.mega_audio_url" class="break-all">
                    <a
                      :href="feedback.mega_audio_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 underline"
                    >
                      {{ t('audioOnMega') }}
                    </a>
                  </div>
                  <div v-if="feedback.mega_error" class="text-red-600 break-all">{{ feedback.mega_error }}</div>
                  <details>
                    <summary class="cursor-pointer text-gray-700">{{ t('rawMetaLabel') }}</summary>
                    <pre class="mt-2 whitespace-pre-wrap break-all text-[11px] text-gray-600">{{ JSON.stringify(feedback.meta || {}, null, 2) }}</pre>
                  </details>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- AI Generated Batches -->
    <div class="border rounded-lg p-4 mb-6">
      <div class="flex items-center justify-between gap-4 mb-3 flex-wrap">
        <h2 class="text-lg font-semibold">{{ t('aiGeneratedTasksTitle') }} 🤖</h2>
        <div class="flex gap-2 items-center flex-wrap">
          <select v-model="generatedBatchStatusFilter" @change="loadGeneratedBatches" class="border rounded px-2 py-1 text-sm">
            <option value="">{{ t('allLabel') }}</option>
            <option value="pending_review">{{ t('statusPendingReview') }}</option>
            <option value="approved">{{ t('statusApproved') }}</option>
            <option value="rejected">{{ t('statusRejected') }}</option>
            <option value="preview">{{ t('statusPreview') }}</option>
            <option value="survey_done">{{ t('statusSurveyDone') }}</option>
          </select>
          <button @click="loadGeneratedBatches" class="bg-violet-600 text-white px-4 py-2 rounded text-sm">
            {{ t('refresh') }}
          </button>
        </div>
      </div>

      <div v-if="generatedBatchesLoading" class="text-gray-500">{{ t('loadingGeneric') }}</div>
      <div v-else-if="generatedBatchesError" class="text-red-600">{{ generatedBatchesError }}</div>
      <div v-else-if="!generatedBatches.length" class="text-gray-500">{{ t('noRecordsFound') }}</div>
      <div v-else class="space-y-4">
        <div
          v-for="batch in generatedBatches"
          :key="batch.id"
          class="border rounded-lg p-4"
        >
          <!-- Header row -->
          <div class="flex items-start justify-between gap-3 mb-2 flex-wrap">
            <div>
              <span class="font-bold text-base">{{ batch.raw_json?.task_name || t('untitledLabel') }}</span>
              <span class="ml-2 text-xs text-gray-500">{{ formatDate(batch.created_at) }} · {{ batch.grade }}. {{ t('grade') }}</span>
            </div>
            <span
              class="text-xs font-bold px-2 py-0.5 rounded-full"
              :class="{
                'bg-amber-100 text-amber-700': batch.status === 'pending_review',
                'bg-emerald-100 text-emerald-700': batch.status === 'approved',
                'bg-red-100 text-red-700': batch.status === 'rejected',
                'bg-slate-100 text-slate-600': batch.status === 'preview' || batch.status === 'survey_done',
              }"
            >
              {{ batch.status }}
            </span>
          </div>

          <!-- Student + description -->
          <div class="text-sm text-gray-600 mb-2">
            <span class="font-semibold">{{ batch.student_username || t('unknownLabel') }}</span>
            <span class="text-gray-400"> (ID {{ batch.student_id }})</span>
          </div>
          <p class="text-sm italic text-gray-500 mb-3">"{{ batch.description }}"</p>

          <!-- Examples preview (collapsible) -->
          <details class="mb-3">
            <summary class="cursor-pointer text-xs font-bold text-violet-600 mb-2">
              {{ t('showExamplesLabel') }} ({{ batch.raw_json?.examples?.length || 0 }})
            </summary>
            <div class="overflow-x-auto mt-2">
              <table class="min-w-full text-xs border-collapse">
                <thead>
                  <tr class="bg-gray-100">
                    <th class="p-1.5 border">{{ t('colExample') }}</th>
                    <th class="p-1.5 border">{{ t('colType') }}</th>
                    <th class="p-1.5 border">{{ t('colAnswer') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(ex, i) in batch.raw_json?.examples" :key="i">
                    <td class="p-1.5 border font-mono">{{ ex.example }}</td>
                    <td class="p-1.5 border text-center">{{ ex.input_type }}</td>
                    <td class="p-1.5 border font-mono text-green-700 font-bold">{{ ex.answer }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>

          <!-- Survey answers (if any) -->
          <div v-if="batch.survey" class="text-xs text-gray-500 mb-3 grid grid-cols-2 gap-x-4 gap-y-1 bg-gray-50 rounded p-2">
            <div>{{ t('surveyQ1Label') }}: <strong>{{ batch.survey.q1_as_requested ? t('yesLabel') : t('noLabel') }}</strong></div>
            <div>{{ t('surveyQ2Label') }}: <strong>{{ batch.survey.q2_solvable_display ? t('yesLabel') : t('noLabel') }}</strong></div>
            <div>{{ t('surveyQ3Label') }}: <strong>{{ batch.survey.q3_difficulty }}</strong></div>
            <div>{{ t('surveyQ4Label') }}: <strong>{{ batch.survey.q4_has_errors ? t('yesLabel') : t('noLabel') }}</strong></div>
            <div class="col-span-2">{{ t('surveyQ5Label') }}: <strong>{{ batch.survey.q5_satisfied ? `✅ ${t('yesLabel')}` : `❌ ${t('noLabel')}` }}</strong></div>
          </div>

          <!-- Approve / Reject (only for pending_review) -->
          <div v-if="batch.status === 'pending_review' || batch.status === 'preview'" class="flex gap-2">
            <button
              @click="approveBatch(batch.id)"
              class="px-4 py-1.5 bg-emerald-600 text-white rounded text-sm font-bold hover:bg-emerald-700"
            >
              ✅ {{ t('approveLabel') }}
            </button>
            <button
              @click="rejectBatch(batch.id)"
              class="px-4 py-1.5 bg-red-500 text-white rounded text-sm font-bold hover:bg-red-600"
            >
              ❌ {{ t('rejectLabel') }}
            </button>
          </div>
          <div v-else-if="batch.rejection_note" class="text-xs text-red-600 mt-1">
            {{ t('reasonLabel') }} {{ batch.rejection_note }}
          </div>
        </div>
      </div>
    </div>

    <!-- Example requests ("Málo príkladov? Klikni sem.") -->
    <div class="border rounded-lg p-4 mb-6">
      <div class="flex items-center justify-between gap-4 mb-3">
        <h2 class="text-lg font-semibold">{{ t('exampleRequestsTitle') }} 💡</h2>
        <button @click="loadExampleRequests" class="bg-violet-600 text-white px-4 py-2 rounded">
          {{ t('refresh') }}
        </button>
      </div>

      <div v-if="requestsLoading" class="text-gray-500">{{ t('loadingGeneric') }}</div>
      <div v-else-if="requestsError" class="text-red-600">{{ requestsError }}</div>
      <div v-else-if="exampleRequests.length === 0" class="text-gray-500">{{ t('noRequestsYet') }}</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">{{ t('colTime') }}</th>
              <th class="p-2 border">{{ t('gradeLevel') }}</th>
              <th class="p-2 border">{{ t('colRequest') }}</th>
              <th class="p-2 border">{{ t('colSource') }}</th>
              <th class="p-2 border">{{ t('colUser') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in exampleRequests" :key="req.id">
              <td class="p-2 border whitespace-nowrap">{{ formatDate(req.created_at) }}</td>
              <td class="p-2 border text-center font-semibold">{{ req.grade ?? '-' }}</td>
              <td class="p-2 border">{{ req.text }}</td>
              <td class="p-2 border text-center">{{ req.source }}</td>
              <td class="p-2 border">
                <div v-if="req.student_id">
                  <div class="font-semibold">{{ req.student_username || t('studentFallbackName') }}</div>
                  <div class="text-xs text-gray-600">ID: {{ req.student_id }}</div>
                </div>
                <div v-else>
                  <div class="font-semibold">{{ t('anonymousLabel') }}</div>
                  <div class="text-xs text-gray-600 break-all">{{ req.anonymous_session_id || '-' }}</div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="mb-4 grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
      <div>
        <label class="block text-sm font-semibold mb-1">{{ t('identityTypeLabel') }}</label>
        <select v-model="identityType" class="border rounded px-3 py-2 w-full">
          <option value="student">{{ t('studentOption') }}</option>
          <option value="session">{{ t('sessionIdOption') }}</option>
        </select>
      </div>

      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">
          {{ identityType === 'student' ? t('filterStudentsLabel') : t('sessionIdOption') }}
        </label>
        <input
          v-model="filterText"
          type="text"
          class="border rounded px-3 py-2 w-full"
          :placeholder="identityType === 'student' ? t('filterStudentsPlaceholder') : t('sessionIdPlaceholder')"
          @keyup.enter="identityType === 'session' ? loadData() : null"
        />
      </div>

      <div>
        <button
          @click="identityType === 'session' ? loadData() : null"
          class="bg-blue-600 text-white px-4 py-2 rounded w-full"
          :class="identityType === 'student' ? 'opacity-60 cursor-not-allowed' : ''"
        >
          {{ t('loadButtonLabel') }}
        </button>
      </div>
    </div>

    <div v-if="identityType === 'student'" class="border rounded-lg p-4 mb-6">
      <h2 class="text-lg font-semibold mb-3">{{ t('allStudentsTitle') }}</h2>
      <div v-if="studentsLoading" class="text-gray-500">{{ t('loadingStudents') }}</div>
      <div v-else-if="allStudents.length === 0" class="text-gray-500">{{ t('noStudentsInDb') }}</div>
      <div v-else class="max-h-64 overflow-auto border rounded">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">{{ t('colName') }}</th>
              <th class="p-2 border text-center">ID</th>
              <th class="p-2 border text-center">{{ t('colAttempts') }}</th>
              <th class="p-2 border text-center">{{ t('accuracy') }}</th>
              <th class="p-2 border text-center">{{ t('colAction') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.student_id">
              <td class="p-2 border font-semibold">{{ student.username }}</td>
              <td class="p-2 border text-center">{{ student.student_id }}</td>
              <td class="p-2 border text-center">{{ student.total_examples }}</td>
              <td class="p-2 border text-center">{{ formatPercent(student.accuracy) }}</td>
              <td class="p-2 border text-center">
                <button
                  class="text-blue-600 underline"
                  @click="selectStudent(student)"
                >
                  {{ t('viewDataLabel') }}
                </button>
              </td>
            </tr>
            <tr v-if="filteredStudents.length === 0">
              <td colspan="5" class="p-4 text-center text-gray-500">{{ t('noStudentMatchesFilter') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="identityType === 'session'" class="border rounded-lg p-4 mb-6">
      <h2 class="text-lg font-semibold mb-3">{{ t('allAnonymousUsersTitle') }}</h2>
      <div v-if="anonymousLoading" class="text-gray-500">{{ t('loadingAnonymousSessions') }}</div>
      <div v-else-if="allAnonymousSessions.length === 0" class="text-gray-500">{{ t('noAnonymousSessionsInDb') }}</div>
      <div v-else class="max-h-64 overflow-auto border rounded">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">{{ t('colUser') }}</th>
              <th class="p-2 border text-center">{{ t('colAttempts') }}</th>
              <th class="p-2 border text-center">{{ t('accuracy') }}</th>
              <th class="p-2 border text-center">{{ t('colLastActivity') }}</th>
              <th class="p-2 border text-center">{{ t('colAction') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="session in filteredAnonymousSessions" :key="session.session_id">
              <td class="p-2 border font-semibold">{{ session.display_name }}</td>
              <td class="p-2 border text-center">{{ session.total_attempts }}</td>
              <td class="p-2 border text-center">{{ formatPercent(session.accuracy) }}</td>
              <td class="p-2 border text-center">{{ formatDate(session.last_activity) }}</td>
              <td class="p-2 border text-center">
                <button
                  class="text-blue-600 underline"
                  @click="selectAnonymousSession(session)"
                >
                  {{ t('viewDataLabel') }}
                </button>
              </td>
            </tr>
            <tr v-if="filteredAnonymousSessions.length === 0">
              <td colspan="5" class="p-4 text-center text-gray-500">{{ t('noAnonymousMatchesFilter') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500">{{ t('loadingGeneric') }}</div>
    <div v-else-if="error" class="text-red-600 mb-4">{{ error }}</div>

    <div v-if="data" class="space-y-6">
      <div class="border rounded-lg p-4 bg-gray-50">
        <h2 class="text-lg font-semibold mb-3">{{ t('summaryTitle') }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><span class="font-semibold">{{ t('colUser') }}:</span> {{ displayUserLabel }}</div>
          <div><span class="font-semibold">{{ t('colType') }}:</span> {{ data.user_type }}</div>
          <div><span class="font-semibold">{{ t('colAttempts') }}:</span> {{ data.summary?.total_attempts ?? 0 }}</div>
          <div><span class="font-semibold">{{ t('evaluatedLabel') }}:</span> {{ data.summary?.evaluated_count ?? 0 }}</div>
          <div><span class="font-semibold">{{ t('correctLabel') }}:</span> {{ data.summary?.correct_count ?? 0 }}</div>
          <div><span class="font-semibold">{{ t('incorrectLabel') }}:</span> {{ data.summary?.incorrect_count ?? 0 }}</div>
          <div><span class="font-semibold">{{ t('accuracy') }}:</span> {{ formatPercent(data.summary?.accuracy) }}</div>
          <div><span class="font-semibold">{{ t('avgTimeLabel') }}:</span> {{ Math.round(data.summary?.avg_duration_ms ?? 0) }} ms</div>
        </div>
      </div>

      <div class="border rounded-lg p-4">
        <h2 class="text-lg font-semibold mb-3">{{ t('allAttemptsTitle') }}</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full border-collapse text-sm">
            <thead>
              <tr class="bg-gray-100">
                <th class="p-2 border">{{ t('colTime') }}</th>
                <th class="p-2 border">{{ t('colExample') }}</th>
                <th class="p-2 border">{{ t('colTranscript') }}</th>
                <th class="p-2 border">{{ t('colYourAnswer') }}</th>
                <th class="p-2 border">{{ t('correctAnswer') }}</th>
                <th class="p-2 border">{{ t('correctLabel') }}</th>
                <th class="p-2 border">{{ t('colTimeMs') }}</th>
                <th class="p-2 border">{{ t('colCategories') }}</th>
                <th class="p-2 border">{{ t('colPairedRecord') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="attempt in data.all_attempts" :key="attempt.attempt_id">
                <td class="p-2 border whitespace-nowrap">{{ formatDate(attempt.timestamp) }}</td>
                <td class="p-2 border">{{ attempt.example_problem }}</td>
                <td class="p-2 border">{{ attempt.transcription }}</td>
                <td class="p-2 border">{{ attempt.your_answer }}</td>
                <td class="p-2 border">{{ attempt.correct_answer }}</td>
                <td class="p-2 border text-center">
                  <span v-if="attempt.is_correct === true" class="text-green-700 font-semibold">{{ t('yesLabel') }}</span>
                  <span v-else-if="attempt.is_correct === false" class="text-red-700 font-semibold">{{ t('noLabel') }}</span>
                  <span v-else class="text-gray-500">-</span>
                </td>
                <td class="p-2 border text-center">{{ attempt.duration_ms }}</td>
                <td class="p-2 border">{{ (attempt.practiced_skills?.names || []).join(', ') }}</td>
                <td class="p-2 border">
                  <div v-if="attempt.audio_url || attempt.paired_json_url" class="space-y-2 min-w-56">
                    <audio :src="attempt.audio_url" controls preload="none" class="w-full" />
                    <div class="flex items-center gap-2 text-xs">
                      <a
                        v-if="attempt.paired_json_url"
                        :href="attempt.paired_json_url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 underline"
                      >
                        {{ t('jsonSidecarLabel') }}
                      </a>
                      <span v-else class="text-gray-500">{{ t('jsonSidecarLabel') }}: -</span>
                    </div>
                    <div class="text-xs text-gray-600 break-all">{{ attempt.audio_file || '' }}</div>
                  </div>
                  <span v-else class="text-gray-500">-</span>
                </td>
              </tr>
              <tr v-if="!data.all_attempts || data.all_attempts.length === 0">
                <td colspan="9" class="p-4 text-center text-gray-500">{{ t('noAttemptsYet') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="border rounded-lg p-4 bg-gray-50">
        <h2 class="text-lg font-semibold mb-3">{{ t('rawJsonTitle') }}</h2>
        <pre class="text-xs overflow-auto whitespace-pre-wrap break-all">{{ prettyJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAllAnonymousSessionsStats, getAllStudentsStats, getExampleReports, getAllExampleRequests, getMyData, getSurveyFeedbacks, getAllGeneratedBatches, approveGeneratedBatch, rejectGeneratedBatch } from '@/api/apiClient'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const identityType = ref('student')
const identityValue = ref('')
const filterText = ref('')
const loading = ref(false)
const studentsLoading = ref(false)
const anonymousLoading = ref(false)
const error = ref('')
const data = ref(null)
const selectedStudentName = ref('')
const allStudents = ref([])
const allAnonymousSessions = ref([])
const reportsLoading = ref(false)
const reportsError = ref('')
const exampleReports = ref([])
const feedbacksLoading = ref(false)
const feedbacksError = ref('')
const surveyFeedbacks = ref([])
const requestsLoading = ref(false)
const requestsError = ref('')
const exampleRequests = ref([])
const generatedBatchesLoading = ref(false)
const generatedBatchesError = ref('')
const generatedBatches = ref([])
const generatedBatchStatusFilter = ref('')

const filteredStudents = computed(() => {
  const text = (filterText.value || '').trim().toLowerCase()
  if (!text) return allStudents.value

  return allStudents.value.filter((student) => {
    const username = (student.username || '').toLowerCase()
    const idString = String(student.student_id || '')
    return username.includes(text) || idString.includes(text)
  })
})

const filteredAnonymousSessions = computed(() => {
  const text = (filterText.value || '').trim().toLowerCase()
  if (!text) return allAnonymousSessions.value

  return allAnonymousSessions.value.filter((session) => {
    const displayName = (session.display_name || '').toLowerCase()
    const idText = (session.session_id || '').toLowerCase()
    return displayName.includes(text) || idText.includes(text)
  })
})

const prettyJson = computed(() => {
  if (!data.value) return ''
  return JSON.stringify(data.value, null, 2)
})

const displayUserLabel = computed(() => {
  if (!data.value) return '-'
  if (data.value.user_type === 'anonymous_session') {
    const raw = String(data.value.user_id || '')
    const suffix = raw.slice(0, 6) || 'unknown'
    return `anonym${suffix}`
  }
  return selectedStudentName.value || String(data.value.user_id || '-')
})

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatPercent(value) {
  if (value === null || value === undefined) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function formatReportType(value) {
  const mapping = {
    wrong_answer: t('reportWrongAnswer'),
    wrong_grade: t('reportWrongGrade'),
    unclear: t('reportUnclear'),
    other: t('reportOther'),
  }
  return mapping[value] || value || '-'
}

function formatFeedbackType(value) {
  const mapping = {
    'final-feedback-text': t('feedbackTypeFinalText'),
    'final-feedback-voice': t('feedbackTypeFinalVoice'),
    'survey-choice': t('feedbackTypeSurveyChoice'),
    'survey-scale': t('feedbackTypeSurveyScale'),
    'survey-voice': t('feedbackTypeSurveyVoice'),
  }
  return mapping[value] || value || '-'
}

async function loadStudents() {
  studentsLoading.value = true
  try {
    allStudents.value = await getAllStudentsStats()
  } catch (e) {
    error.value = typeof e === 'string' ? e : t('errorLoadingStudents')
  } finally {
    studentsLoading.value = false
  }
}

async function loadAnonymousSessions() {
  anonymousLoading.value = true
  try {
    allAnonymousSessions.value = await getAllAnonymousSessionsStats()
  } catch (e) {
    error.value = typeof e === 'string' ? e : t('errorLoadingAnonymousSessions')
  } finally {
    anonymousLoading.value = false
  }
}

async function loadReports() {
  reportsLoading.value = true
  reportsError.value = ''
  try {
    exampleReports.value = await getExampleReports(1000)
  } catch (e) {
    reportsError.value = typeof e === 'string' ? e : t('errorLoadingReports')
  } finally {
    reportsLoading.value = false
  }
}

async function loadSurveyFeedbacks() {
  feedbacksLoading.value = true
  feedbacksError.value = ''
  try {
    surveyFeedbacks.value = await getSurveyFeedbacks(1000)
  } catch (e) {
    feedbacksError.value = typeof e === 'string' ? e : t('errorLoadingFeedbacks')
  } finally {
    feedbacksLoading.value = false
  }
}

async function loadExampleRequests() {
  requestsLoading.value = true
  requestsError.value = ''
  try {
    exampleRequests.value = await getAllExampleRequests(1000)
  } catch (e) {
    requestsError.value = typeof e === 'string' ? e : t('errorLoadingRequests')
  } finally {
    requestsLoading.value = false
  }
}

async function loadGeneratedBatches() {
  generatedBatchesLoading.value = true
  generatedBatchesError.value = ''
  try {
    const params = {}
    if (generatedBatchStatusFilter.value) params.status = generatedBatchStatusFilter.value
    generatedBatches.value = await getAllGeneratedBatches(params)
  } catch (e) {
    generatedBatchesError.value = typeof e === 'string' ? e : t('errorLoadingGeneric')
  } finally {
    generatedBatchesLoading.value = false
  }
}

async function approveBatch(batchId) {
  try {
    await approveGeneratedBatch(batchId)
    await loadGeneratedBatches()
  } catch (e) {
    alert(typeof e === 'string' ? e : t('errorApproving'))
  }
}

async function rejectBatch(batchId) {
  const note = prompt(t('rejectionReasonPrompt')) ?? ''
  try {
    await rejectGeneratedBatch(batchId, note)
    await loadGeneratedBatches()
  } catch (e) {
    alert(typeof e === 'string' ? e : t('errorRejecting'))
  }
}

async function selectStudent(student) {
  identityType.value = 'student'
  identityValue.value = String(student.student_id)
  selectedStudentName.value = student.username
  await loadData()
}

async function selectAnonymousSession(session) {
  identityType.value = 'session'
  filterText.value = String(session.session_id || '')
  selectedStudentName.value = session.display_name || ''
  await loadData()
}

async function loadData() {
  if (identityType.value === 'student' && !identityValue.value) {
    error.value = t('selectStudentFromListError')
    return
  }

  if (identityType.value === 'session' && !filterText.value) {
    error.value = t('enterStudentOrSessionIdError')
    return
  }

  loading.value = true
  error.value = ''

  try {
    const payload = identityType.value === 'student'
      ? { student_id: identityValue.value }
      : { session_id: filterText.value }

    data.value = await getMyData(payload)
  } catch (e) {
    error.value = typeof e === 'string' ? e : t('errorLoadingData')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStudents()
  loadAnonymousSessions()
  loadReports()
  loadSurveyFeedbacks()
  loadExampleRequests()
  loadGeneratedBatches()
})
</script>

<style scoped>
table { border-collapse: collapse; }
th, td { text-align: left; vertical-align: top; }
</style>
