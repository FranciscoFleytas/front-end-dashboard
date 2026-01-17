<script setup lang="ts">
import { ref, computed } from 'vue'
import { email } from 'zod'
import type { StepperItem } from '@nuxt/ui'
import ConfirmModal from '@/components/poner-precio/ConfirmModal.vue'

const title = 'Define tu precio'
const description = 'Establece tu estrategia de precios. Elige el modelo que mejor se adapte a tu negocio.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description
})


const steperItems = ref<StepperItem[]>([
  {
    slot: 'user-info' as const,
    title: 'Información del usuario', 
    description: 'Proporciona los detalles de tu cuenta', 
    icon: 'i-lucide-user'
  },
  { 
    slot: 'price-setting' as const,
    title: 'Configura tu servicio', 
    description: 'Establece el punto de partida para tu estrategia', 
    icon: 'i-lucide-sliders-horizontal'
  },
  { 
    slot: 'review-order' as const,
    title: 'Confirma tu pedido', 
    description: 'Revisa y confirma los detalles de tu compra', 
    icon: 'i-lucide-check-circle' 
  }
])

const stepperActiveStep = ref(0)

const stepper = useTemplateRef('stepper')

const dataModel = ref({
  email: '',
  username: '',
  follows: 0,
  likes: 0,
  views: 0,
  comments: 0
})

const API_BASE = 'http://localhost:8000'

type UserSearchResult = {
  id: number
  label: string
  suffix: string
  link_instagram: string
  avatar: { src: string }
}

const profileResult = ref<UserSearchResult | null>(null)
const profileLoading = ref(false)
const profileError = ref<string | null>(null)

const normalizedUsername = computed(() => {
  const u = (dataModel.value.username || '').trim()
  return u.startsWith('@') ? u.slice(1) : u
})

const canContinueUserInfo = computed(() => {
  return !!dataModel.value.email.trim() && !!normalizedUsername.value.trim() && !!profileResult.value && !profileLoading.value
})

const fetchProfile = async () => {
  profileError.value = null
  profileResult.value = null

  const u = normalizedUsername.value.trim()
  if (!u) return

  profileLoading.value = true
  try {
    // Usamos el endpoint que ya funciona (devuelve un solo objeto)
    const res = await $fetch<UserSearchResult>(`${API_BASE}/api/users/search`, {
      params: {
        q: u,
        email: dataModel.value.email.trim() || undefined
      }
    })

    profileResult.value = res
  } catch (e: any) {
    profileResult.value = null
    profileError.value = 'No pudimos validar ese usuario. Verifica que exista y que esté bien escrito.'
  } finally {
    profileLoading.value = false
  }
}


// Slider configuration options
const sliderOptions = {
  follows: {
    min: 0,
    max: 50000,
    step: 100,
    ticks: [0, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000],
    price: 0.10 // Precio por cada 1000 follows
  },
  likes: {
    min: 0,
    max: 10000,
    step: 50,
    ticks: [0, 100, 500, 1000, 2500, 5000, 10000],
    price: 0.15 // Precio por cada 1000 likes
  },
  views: {
    min: 0,
    max: 50000,
    step: 100,
    ticks: [0, 500, 1000, 5000, 10000, 25000, 50000],
    price: 0.05 // Precio por cada 1000 views
  },
  comments: {
    min: 0,
    max: 1000,
    step: 10,
    ticks: [0, 10, 50, 100, 250, 500, 1000],
    price: 0.50 // Precio por cada 1000 comments
  }
}

const formattedFollows = computed(() => new Intl.NumberFormat().format(dataModel.value.follows))
const formattedLikes = computed(() => new Intl.NumberFormat().format(dataModel.value.likes))
const formattedViews = computed(() => new Intl.NumberFormat().format(dataModel.value.views))
const formattedComments = computed(() => new Intl.NumberFormat().format(dataModel.value.comments))

const totalPriceFollows = computed(() => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(sliderOptions.follows.price * (dataModel.value.follows / 1000)))
const totalPriceLikes = computed(() => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(sliderOptions.likes.price * (dataModel.value.likes / 1000)))
const totalPriceViews = computed(() => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(sliderOptions.views.price * (dataModel.value.views / 1000)))
const totalPriceComments = computed(() => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(sliderOptions.comments.price * (dataModel.value.comments / 1000)))

const totalGeneral = computed(() => {
  const total = 
    sliderOptions.follows.price * (dataModel.value.follows / 1000) +
    sliderOptions.likes.price * (dataModel.value.likes / 1000) +
    sliderOptions.views.price * (dataModel.value.views / 1000) +
    sliderOptions.comments.price * (dataModel.value.comments / 1000)
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(total)
})

const totalNumeric = computed(() => 
  sliderOptions.follows.price * (dataModel.value.follows / 1000) +
  sliderOptions.likes.price * (dataModel.value.likes / 1000) +
  sliderOptions.views.price * (dataModel.value.views / 1000) +
  sliderOptions.comments.price * (dataModel.value.comments / 1000)
)

const { $toast } = useNuxtApp()

const toast = useToast()

const verfyUserInfo = async () => {
  // Validaciones
  if (!dataModel.value.email.trim()) {
    toast.add({ title: 'Error', description: 'Por favor ingresa tu correo electrónico', color: 'error' })
    return
  }

  if (!dataModel.value.username.trim()) {
    toast.add({ title: 'Error', description: 'Por favor ingresa tu nombre de usuario de Instagram', color: 'error' })
    return
  }

  // Validar/preview del perfil antes de avanzar
  if (!profileResult.value) {
    await fetchProfile()
  }

  if (!profileResult.value) {
    toast.add({ title: 'Error', description: 'No pudimos validar tu usuario de Instagram. Revisa el @ y vuelve a intentar.', color: 'error' })
    return
  }

  stepper.value?.next()
}


const verifyForm = async () => {
  
  if (totalNumeric.value <= 0) {
    toast.add({ title: 'Error', description: 'Debes seleccionar al menos un servicio', color: 'error' })
    return
  }
  
  stepper.value?.next()
  
}

const overlay = useOverlay()
const modal = overlay.create(ConfirmModal)

const handleConfirmOrder = async () => {

  const instance = modal.open()

  const shouldSendOrder = await instance.result

  if (!shouldSendOrder) {
    return
  }

  // Implementar lógica de envío
  console.log({
    email: dataModel.value.email,
    username: dataModel.value.username,
    follows: dataModel.value.follows,
    likes: dataModel.value.likes,
    views: dataModel.value.views,
    comments: dataModel.value.comments,
    total: totalNumeric.value
  })

  toast.add({ title: 'Pedido confirmado', description: 'Tu pedido ha sido confirmado exitosamente', color: 'success' }) 
}


</script>

<template>
  <div>
    <!-- Configuration Section -->
    <UPageSection
      title="Configura tu precio"
      description="Establece el punto de partida para tu estrategia"
    >

      <UStepper disabled v-model="stepperActiveStep" ref="stepper" :items="steperItems" :active-step="0" class="mb-6" > 
        
        <!-- User info -->
        <template #user-info>
          <div class="min-w-full sm:min-w-lg max-w-2xl mx-auto mt-6">
            <UCard>

              <template #header>
                <h3 class="text-xl font-semibold">Información del usuario</h3>
                <p class="text-sm text-muted">Proporciona los detalles de tu cuenta</p>
              </template>

              <form @submit.prevent="verfyUserInfo" class="space-y-6">
                
                <!-- Email Input -->
                <UFormGroup label="Correo electronico" hint="El correo al cual se enviarán las notificaciones">
                  <UFormField
                    name="email"
                    label="Tu correo electronico"
                    class="pt-4 pb-2 select-none"
                    required>
                    <UInput
                      v-model.string="dataModel.email"
                      type="email"
                      placeholder="tu_correo@ejemplo.com"
                      min="0"
                      step="10"
                      class="w-full"
                      icon="i-lucide-mail"
                    />
                  </UFormField>
                </UFormGroup>

                <!-- Username Input -->
                <UFormGroup label="Nombre de usuario de instagram" hint="Tu precio inicial de referencia">
                  <UFormField
                    name="username"
                    label="Nombre de usuario de instagram"
                    class="pt-4 pb-2 select-none"
                    required>
                    <UInput
                      v-model.string="dataModel.username"
                      type="text"
                      placeholder="usuario_instagram"
                      min="0"
                      step="10"
                      class="w-full"
                      icon="i-lucide-at-sign"
                      @blur="fetchProfile"
                      @keydown.enter.prevent="fetchProfile"
                    />

                  <div class="mt-3">
                    <div v-if="profileLoading" class="text-sm text-muted">
                      Buscando perfil…
                    </div>

                    <div v-else-if="profileError" class="text-sm text-red-500">
                      {{ profileError }}
                    </div>

                    <UCard v-else-if="profileResult" class="mt-2">
                      <div class="flex items-center gap-3">
                        <img
                          v-if="profileResult?.avatar?.src"
                          :src="profileResult.avatar.src"
                          alt="avatar"
                          class="h-10 w-10 rounded-full object-cover"
                        />
                        <div
                          v-else
                          class="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground"
                        >
                          @
                        </div>
                        <div class="flex-1">
                          <div class="font-semibold leading-tight">
                            {{ profileResult.label }}
                          </div>
                          <a
                            class="text-sm text-primary underline"
                            :href="profileResult.link_instagram"
                            target="_blank"
                            rel="noreferrer"
                          >
                            {{ profileResult.link_instagram }}
                          </a>
                        </div>
                      </div>
                    </UCard>
                  </div>
  
                  </UFormField>
                </UFormGroup>

                <!-- CTA Buttons -->
                <div class="flex flex-col gap-3 pt-4 mt-6">
                  <UButton
                    type="submit"
                    label="Continuar"
                    size="lg"
                    block
                    color="primary"
                  />
                </div>
              </form>
            </UCard>
          </div>
        </template>

        <!-- Price setting -->
        <template #price-setting>
          <div class="min-w-full sm:min-w-lg max-w-2xl mx-auto mt-6">
            <UCard>

              <template #header>
                <h3 class="text-xl font-semibold">Configura tu servicio</h3>
                <p class="text-sm text-muted">Establece el punto de partida para tu estrategia</p>
              </template>

              <form @submit.prevent="verifyForm" class="space-y-6">

                <!-- Follows slider -->
                <UFormGroup label="Cantidad de follows" hint="Cantidad aproximada de seguidores a agregar" >
                  <UFormField class="pt-4 pb-2 select-none" label="Seguidores">
                    <RangeInput
                      v-model="dataModel.follows"
                      :min="sliderOptions.follows.min"
                      :max="sliderOptions.follows.max"
                      :step="sliderOptions.follows.step"
                      :ticks="sliderOptions.follows.ticks"
                      :format-tick="(value : number) => new Intl.NumberFormat().format(value)"
                    />
                    
                    <div class="flex items-center justify-between select-none">
                      <span class="font-semibold">{{ formattedFollows }} follows</span>
                      <span class="font-bold text-primary">{{ totalPriceFollows }}</span>
                    </div>
                  </UFormField>
                </UFormGroup>

                <!-- Likes slider -->
                <UFormGroup label="Cantidad de likes" hint="Cantidad aproximada de likes a agregar">
                  <UFormField class="pt-4 pb-2 select-none" label="Likes">
                    <RangeInput
                      v-model="dataModel.likes"
                      :min="sliderOptions.likes.min"
                      :max="sliderOptions.likes.max"
                      :step="sliderOptions.likes.step"
                      :ticks="sliderOptions.likes.ticks"
                      :format-tick="(value: number) => new Intl.NumberFormat().format(value)"
                    />

                    <div class="flex items-center justify-between select-none">
                      <span class="font-semibold">{{ formattedLikes }} likes</span>
                      <span class="font-bold text-primary">{{ totalPriceLikes }}</span>
                    </div>
                  </UFormField>
                </UFormGroup>

                <!-- Views slider -->
                <UFormGroup label="Cantidad de views" hint="Cantidad aproximada de vistas a agregar">
                  <UFormField class="pt-4 pb-2 select-none" label="Vistas">
                    <RangeInput
                      v-model="dataModel.views"
                      :min="sliderOptions.views.min"
                      :max="sliderOptions.views.max"
                      :step="sliderOptions.views.step"
                      :ticks="sliderOptions.views.ticks"
                      :format-tick="(value: number) => new Intl.NumberFormat().format(value)"
                    />

                    <div class="flex items-center justify-between select-none">
                      <span class="font-semibold">{{ formattedViews }} views</span>
                      <span class="font-bold text-primary">{{ totalPriceViews }}</span>
                    </div>
                  </UFormField>
                </UFormGroup>

                <!-- Comments slider -->
                <UFormGroup label="Cantidad de comments" hint="Cantidad aproximada de comentarios a agregar">
                  <UFormField class="pt-4 pb-2 select-none" label="Comentarios">
                    <RangeInput
                      v-model="dataModel.comments"
                      :min="sliderOptions.comments.min"
                      :max="sliderOptions.comments.max"
                      :step="sliderOptions.comments.step"
                      :ticks="sliderOptions.comments.ticks"
                      :format-tick="(value: number) => new Intl.NumberFormat().format(value)"
                    />

                    <div class="flex items-center justify-between select-none">
                      <span class="font-semibold">{{ formattedComments }} comments</span>
                      <span class="font-bold text-primary">{{ totalPriceComments }}</span>
                    </div>
                  </UFormField>
                </UFormGroup>


                <USeparator type="dashed" size="lg" class="my-4"/>

                <!-- Total Price -->
                <div>
                  <div class="flex items-center justify-between text-lg font-bold">
                    <span>Total a pagar:</span>
                    <span class="text-primary">{{ totalGeneral }}</span>
                  </div>
                </div>

                <!-- CTA Buttons -->
                <div class="flex flex-col gap-3 pt-4">
                  <UButton
                    type="submit"
                    label="Guardar configuración"
                    size="lg"
                    block
                  />
                  <UButton
                    label="Editar usuario"
                    size="lg"
                    @click="stepper?.prev()"
                    block
                    variant="outline"
                    color="primary"
                  />
                </div>
              </form>
            </UCard>
          </div>
        </template>

        <!-- Review order -->
        <template #review-order>
          <div class="min-w-full sm:min-w-lg max-w-2xl mx-auto mt-6">
            <UCard>
              <template #header>
                <h3 class="text-xl font-semibold">Confirma tu pedido</h3>
                <p class="text-sm text-muted">Revisa y confirma los detalles de tu compra</p>
              </template>
              <div class="space-y-6">
                <h3 class="text-xl font-semibold">Resumen de tu pedido</h3>

                <!-- Order details -->
                <div class="space-y-4">
                  <div class="flex justify-between items-center">
                    <span class="text-sm text-muted">Correo electronico</span>
                    <span class="font-medium">{{ dataModel.email }}</span>
                  </div>
                  <div class="flex justify-between items-center">
                    <span class="text-sm text-muted">Usuario de Instagram:</span>
                    <span class="font-medium">@{{ dataModel.username }}</span>
                  </div>

                  <USeparator />

                  <div v-if="dataModel.follows > 0" class="flex justify-between items-center">
                    <span class="text-sm">Seguidores: {{ formattedFollows }}</span>
                    <span class="font-medium text-primary">{{ totalPriceFollows }}</span>
                  </div>

                  <div v-if="dataModel.likes > 0" class="flex justify-between items-center">
                    <span class="text-sm">Likes: {{ formattedLikes }}</span>
                    <span class="font-medium text-primary">{{ totalPriceLikes }}</span>
                  </div>

                  <div v-if="dataModel.views > 0" class="flex justify-between items-center">
                    <span class="text-sm">Vistas: {{ formattedViews }}</span>
                    <span class="font-medium text-primary">{{ totalPriceViews }}</span>
                  </div>

                  <div v-if="dataModel.comments > 0" class="flex justify-between items-center">
                    <span class="text-sm">Comentarios: {{ formattedComments }}</span>
                    <span class="font-medium text-primary">{{ totalPriceComments }}</span>
                  </div>

                  <USeparator />

                  <div class="flex justify-between items-center text-lg font-bold">
                    <span>Total a pagar:</span>
                    <span class="text-primary">{{ totalGeneral }}</span>
                  </div>
                </div>

                <!-- CTA Buttons -->
                <div class="flex flex-col gap-3 pt-4">
                  <UButton
                    label="Confirmar pedido"
                    size="lg"
                    @click="handleConfirmOrder"
                    block
                    color="primary"
                  />
                  <UButton
                    label="Editar el pedido"
                    size="lg"
                    @click="stepper?.prev()"
                    block
                    variant="outline"
                    color="primary"
                  />
                </div>
              </div>
            </UCard>
          </div>
        </template>
      </UStepper>

      
    </UPageSection>

    <!-- Benefits Section -->
    <UPageSection
      title="Ventajas de definir tu estrategia"
      description="Optimiza tus ingresos y crecimiento"
      class="bg-elevated/50"
    >
      <UPageGrid>
        <UPageCard
          title="Mayor Control"
          description="Administra completamente tu estrategia de precios según tu capacidad"
          icon="i-lucide-sliders-horizontal"
          variant="subtle"
          spotlight
        />
        <UPageCard
          title="Flexibilidad"
          description="Ajusta tus precios en tiempo real según demanda del mercado"
          icon="i-lucide-zap"
          variant="subtle"
          spotlight
        />
        <UPageCard
          title="Crecimiento Escalable"
          description="Aumenta tus ingresos a medida que crece tu operación"
          icon="i-lucide-trending-up"
          variant="subtle"
          spotlight
        />
      </UPageGrid>
    </UPageSection>
  </div>
</template>
