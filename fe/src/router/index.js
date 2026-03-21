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
import BulkImportView from '@/views/BulkImportView.vue'
import LeaderboardView from '@/views/LeaderboardView.vue'
import PokrokView from '@/views/PokrokView.vue'

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
  } else {
    next();
  }
});

export default router
