<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({
  layout: 'auth'
})

useSeoMeta({
  title: 'Sign up',
  description: 'Create an account to get started'
})

const { signup, loading } = useAuth()

const fields = [{
  name: 'name',
  type: 'text' as const,
  label: 'Name',
  placeholder: 'Enter your name',
  required: true
}, {
  name: 'email',
  type: 'text' as const,
  label: 'Email',
  placeholder: 'Enter your email',
  required: true
}, {
  name: 'password',
  label: 'Password',
  type: 'password' as const,
  placeholder: 'Enter your password',
  required: true
}]

const providers = [{
  label: 'Google',
  icon: 'i-simple-icons-google',
  onClick: () => {
    const toast = useToast()
    toast.add({ title: 'Google', description: 'Sign up with Google' })
  }
}, {
  label: 'GitHub',
  icon: 'i-simple-icons-github',
  onClick: () => {
    const toast = useToast()
    toast.add({ title: 'GitHub', description: 'Sign up with GitHub' })
  }
}]

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.email('Invalid email'),
  password: z.string().min(8, 'Must be at least 8 characters')
})

type Schema = z.output<typeof schema>

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  const result = await signup(payload.data.name, payload.data.email, payload.data.password)

  if (!result.success) {
    const toast = useToast()
    toast.add({
      title: 'Signup failed',
      description: result.error || 'Something went wrong',
      icon: 'i-lucide-alert-circle',
      color: 'error'
    })
  }
}
</script>

<template>
  <UAuthForm
    :fields="fields"
    :schema="schema"
    :providers="providers"
    :submit="{ label: 'Create account', loading: loading }"
    title="Create an account"
    @submit="onSubmit"
  >
    <template #description>
      Already have an account? <ULink
        to="/login"
        class="text-primary font-medium"
      >Login</ULink>.
    </template>

    <template #footer>
      By signing up, you agree to our <ULink
        to="/terms"
        class="text-primary font-medium"
      >Terms of Service</ULink> and <ULink
        to="/privacy"
        class="text-primary font-medium"
      >Privacy Policy</ULink>.
    </template>
  </UAuthForm>
</template>
