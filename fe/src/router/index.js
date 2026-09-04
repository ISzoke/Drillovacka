import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/useAuthStore'

// Import views
import HomeView from '@/views/HomeView.vue'
import TopicView from '@/views/TopicView.vue'
import ExampleView from '@/views/ExampleView.vue'
import SandboxView from '@/views/SandboxView.vue'
import TasksView from '@/views/TasksView.vue'
import TaskGradeManagerView from '@/views/TaskGradeManagerView.vue'
import SkillCreatorView from '@/views/SkillCreatorView.vue'
import ProfileView from '@/views/ProfileView.vue'
import AdminView from '@/views/AdminView.vue'
import GradeTopicsView from '@/views/GradeTopicsView.vue'
import SkillAnalyticsView from '@/views/SkillAnalyticsView.vue'
import AdminMyDataView from '@/views/AdminMyDataView.vue'
import AdminActivityView from '@/views/AdminActivityView.vue'
import AdminEngagementView from '@/views/AdminEngagementView.vue'
import AdminTeachersView from '@/views/AdminTeachersView.vue'
import BulkImportView from '@/views/BulkImportView.vue'
import LeaderboardView from '@/views/LeaderboardView.vue'
import PokrokView from '@/views/PokrokView.vue'
import MyGeneratedBatchesView from '@/views/MyGeneratedBatchesView.vue'
import PracticeGeneratedView from '@/views/PracticeGeneratedView.vue'
import TaskDetailView from '@/views/TaskDetailView.vue'
import ContactView from '@/views/ContactView.vue'

// Teacher views
import TeacherLoginView from '@/views/TeacherLoginView.vue'
import TeacherRegisterView from '@/views/TeacherRegisterView.vue'
import TeacherDashboardView from '@/views/TeacherDashboardView.vue'
import TeacherClassroomView from '@/views/TeacherClassroomView.vue'
import TeacherStudentDetailView from '@/views/TeacherStudentDetailView.vue'
import TeacherAssignTasksView from '@/views/TeacherAssignTasksView.vue'
import TeacherTaskSetsView from '@/views/TeacherTaskSetsView.vue'
import TeacherClassroomStudentView from '@/views/TeacherClassroomStudentView.vue'
import TeacherCreateTaskView from '@/views/TeacherCreateTaskView.vue'
import TeacherEditTaskView from '@/views/TeacherEditTaskView.vue'
import TeacherLibraryView from '@/views/TeacherLibraryView.vue'
import TeacherUnassignedExamplesView from '@/views/TeacherUnassignedExamplesView.vue'
import TeacherPrintView from '@/views/TeacherPrintView.vue'

// Duel (tug-of-war) views
import DuelHomeView from '@/views/DuelHomeView.vue'
import DuelRoomView from '@/views/DuelRoomView.vue'
import QuizHostView from '@/views/QuizHostView.vue'
import QuizPlayView from '@/views/QuizPlayView.vue'

// Student classroom views
import JoinClassroomView from '@/views/JoinClassroomView.vue'
import StudentClassroomsView from '@/views/StudentClassroomsView.vue'
import StudentClassroomDetailView from '@/views/StudentClassroomDetailView.vue'
import ParentPrintView from '@/views/ParentPrintView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { lang: 'sk' }
    },
    {
      path: '/cs',
      name: 'home-cs',
      component: HomeView,
      meta: { lang: 'cs' }
    },
    {
      path: '/en',
      name: 'home-en',
      component: HomeView,
      meta: { lang: 'en' }
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView,
    },
    {
      path: '/topic/:id',
      name: 'topic',
      component: TopicView,
      props: true
    },
    {
      path: '/task/:taskId',
      name: 'taskDetail',
      component: TaskDetailView,
      props: true
    },
    {
      path: '/grade/:gradeId/topics',
      name: 'gradeTopics',
      component: GradeTopicsView,
      props: true
    },
    {
      path: '/examples',
      name: 'examples',
      component: ExampleView,
      props: true
    },
    {
      path: '/sandbox',
      name: 'sandbox',
      component: SandboxView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: TasksView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/tasks/grades',
      name: 'task-grade-manager',
      component: TaskGradeManagerView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/bulk-import',
      name: 'bulk-import',
      component: BulkImportView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/skill-creator',
      name: 'skill-creator',
      component: SkillCreatorView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/analytics/skills',
      name: 'skill-analytics',
      component: SkillAnalyticsView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/analytics/my-data',
      name: 'admin-my-data',
      component: AdminMyDataView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/analytics/activity',
      name: 'admin-activity',
      component: AdminActivityView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/analytics/engagement',
      name: 'admin-engagement',
      component: AdminEngagementView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/admin/teachers',
      name: 'admin-teachers',
      component: AdminTeachersView,
      meta: { requiresAdmin: true }
    },
    {
      path: '/progress',
      name: 'progress',
      component: PokrokView,
      meta: { requiresAuth: true }
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: LeaderboardView,
    },
    {
      path: '/moje-priklady',
      name: 'my-generated-batches',
      component: MyGeneratedBatchesView,
    },
    {
      path: '/prakticovat/:batchId',
      name: 'practice-generated',
      component: PracticeGeneratedView,
      props: true,
    },
    {
      path: '/kontakt',
      name: 'contact',
      component: ContactView,
    },

    // Teacher routes
    {
      path: '/teacher',
      name: 'teacher-login',
      component: TeacherLoginView,
    },
    {
      path: '/teacher/register',
      name: 'teacher-register',
      component: TeacherRegisterView,
    },
    {
      path: '/teacher/dashboard',
      name: 'teacher-dashboard',
      component: TeacherDashboardView,
      meta: { requiresTeacher: true },
    },
    {
      path: '/teacher/classroom/:classroomId',
      name: 'teacher-classroom',
      component: TeacherClassroomView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/student/:studentId',
      name: 'teacher-student-detail',
      component: TeacherStudentDetailView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/assign',
      name: 'teacher-assign-tasks',
      component: TeacherAssignTasksView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/sets',
      name: 'teacher-task-sets',
      component: TeacherTaskSetsView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/student-view',
      name: 'teacher-classroom-student-view',
      component: TeacherClassroomStudentView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/create-task',
      name: 'teacher-create-task',
      component: TeacherCreateTaskView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/classroom/:classroomId/task/:taskId/edit',
      name: 'teacher-edit-task',
      component: TeacherEditTaskView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/quiz/:code',
      name: 'teacher-quiz-host',
      component: QuizHostView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/library',
      name: 'teacher-library',
      component: TeacherLibraryView,
      meta: { requiresTeacher: true },
    },
    {
      path: '/teacher/library/unassigned',
      name: 'teacher-library-unassigned',
      component: TeacherUnassignedExamplesView,
      meta: { requiresTeacher: true },
    },
    {
      path: '/teacher/library/create-task',
      name: 'teacher-create-task-standalone',
      component: TeacherCreateTaskView,
      meta: { requiresTeacher: true },
      props: true,
    },
    {
      path: '/teacher/print',
      name: 'teacher-print',
      component: TeacherPrintView,
      meta: { requiresTeacher: true },
    },
    {
      path: '/teacher/library/task/:taskId/edit',
      name: 'teacher-edit-task-standalone',
      component: TeacherEditTaskView,
      meta: { requiresTeacher: true },
      props: true,
    },

    // Student classroom routes
    {
      path: '/join',
      name: 'join-classroom-manual',
      component: JoinClassroomView,
    },
    {
      path: '/join/:code',
      name: 'join-classroom',
      component: JoinClassroomView,
      props: true,
    },
    {
      path: '/my-classrooms',
      name: 'student-classrooms',
      component: StudentClassroomsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/classroom/:classroomId',
      name: 'student-classroom-detail',
      component: StudentClassroomDetailView,
      meta: { requiresAuth: true },
      props: true,
    },
    {
      path: '/skusobna-pisomka',
      name: 'parent-print',
      component: ParentPrintView,
    },

    // Duel (tug-of-war) — open to anonymous and registered users alike
    {
      path: '/duel',
      name: 'duel-home',
      component: DuelHomeView,
    },
    {
      path: '/duel/:code',
      name: 'duel-room',
      component: DuelRoomView,
      props: true,
    },

    // Live quiz — teacher hosts (see teacher-quiz-host above), open join for anonymous/registered
    {
      path: '/quiz',
      name: 'quiz-join-manual',
      component: QuizPlayView,
    },
    {
      path: '/quiz/:code',
      name: 'quiz-play',
      component: QuizPlayView,
      props: true,
    },
  ]
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAdmin) {
    if (authStore.isAuthenticated && authStore.role === 'admin') {
      next();
    } else {
      next({ name: 'home' });
    }
  } else if (to.meta.requiresTeacher) {
    if (authStore.isAuthenticated && authStore.role === 'teacher') {
      next();
    } else {
      next({ name: 'teacher-login' });
    }
  } else if (to.meta.requiresAuth) {
    if (authStore.isAuthenticated && authStore.role === 'student') {
      next();
    } else {
      next({ name: 'home' });
    }
  } else if (to.name === 'home' && authStore.isAuthenticated && authStore.role === 'teacher') {
    next({ name: 'teacher-dashboard' });
  } else {
    next();
  }
});

export default router
