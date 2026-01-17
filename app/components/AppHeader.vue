<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const { user, logout, isAuthenticated } = useAuth()

const items = computed(() => [{
  label: 'Precio',
  to: '/pricing'
},
{
  label: 'Poner mi precio', 
  to: '/poner-precio'
},])

const userMenuItems = computed<DropdownMenuItem[][]>(() => [[{
  label: user.value?.name || 'User',
  slot: 'account',
  disabled: true
}, {
  type: 'separator'
}, {
  label: 'Dashboard',
  icon: 'i-lucide-layout-dashboard',
  to: '/dashboard'
}, {
  label: 'Settings',
  icon: 'i-lucide-settings',
  to: '/dashboard/settings'
}, {
  type: 'separator'
}, {
  label: 'Sign out',
  icon: 'i-lucide-log-out',
  onSelect: () => logout()
}]])
</script>

<template>
  <UHeader>
    <template #left>
      <NuxtLink to="/">
        Growza
      </NuxtLink>
      <TemplateMenu />
    </template>

    <UNavigationMenu :items="items" variant="link" />

    <template #right>
      <UColorModeButton />

      <template v-if="isAuthenticated">
        <UDropdownMenu :items="userMenuItems">
          <UAvatar :src="user?.avatar || undefined" :alt="user?.name" />
        </UDropdownMenu>
      </template>
      <!--
      
      
        <template v-else>
          <UButton
            label="Sign in"
            color="neutral"
            variant="outline"
            to="/login"
          />
          <UButton label="Sign up" to="/signup" />
        </template>
      -->
    </template>
  </UHeader>
</template>
