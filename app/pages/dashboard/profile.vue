<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({
  layout: 'dashboard'
})

const { user, logout } = useAuth()

const toast = useToast()
const loading = ref(false)

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.email('Invalid email')
})

type Schema = z.output<typeof schema>

const state = reactive({
  name: user.value?.name || '',
  email: user.value?.email || ''
})

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  loading.value = true

  try {
    await new Promise(resolve => setTimeout(resolve, 1000))

    user.value = {
      ...user.value!,
      name: payload.data.name,
      email: payload.data.email
    }

    toast.add({
      title: 'Profile updated',
      description: 'Your profile has been updated successfully.',
      icon: 'i-lucide-check-circle',
      color: 'success'
    })
  } catch {
    toast.add({
      title: 'Update failed',
      description: 'Something went wrong. Please try again.',
      icon: 'i-lucide-alert-circle',
      color: 'error'
    })
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  await logout()
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Profile">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="max-w-2xl mx-auto space-y-6">
        <UPageCard>
          <div class="flex items-center gap-4">
            <UAvatar :src="user?.avatar || undefined" :alt="user?.name" size="xl" />
            <div>
              <h2 class="text-xl font-semibold">
                {{ user?.name }}
              </h2>
              <p class="text-muted">
                {{ user?.email }}
              </p>
            </div>
          </div>
        </UPageCard>

        <UPageCard>
          <template #header>
            <h3 class="text-lg font-semibold">
              Edit Profile
            </h3>
          </template>

          <UForm
            :schema="schema"
            :state="state"
            class="space-y-4"
            @submit="onSubmit"
          >
            <UFormField name="name" label="Name">
              <UInput v-model="state.name" placeholder="Enter your name" />
            </UFormField>

            <UFormField name="email" label="Email">
              <UInput v-model="state.email" type="email" placeholder="Enter your email" />
            </UFormField>

            <div class="flex justify-end gap-3">
              <UButton type="submit" :loading="loading" label="Save Changes" />
            </div>
          </UForm>
        </UPageCard>

        <UPageCard>
          <template #header>
            <h3 class="text-lg font-semibold">
              Account
            </h3>
          </template>

          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium">
                  Delete Account
                </p>
                <p class="text-sm text-muted">
                  Permanently delete your account and all data.
                </p>
              </div>
              <UButton
                color="error"
                variant="outline"
                label="Delete"
                @click="handleLogout"
              />
            </div>
          </div>
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>
