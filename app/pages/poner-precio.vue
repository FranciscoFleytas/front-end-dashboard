<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { StepperItem } from '@nuxt/ui'
import ConfirmModal from '@/components/poner-precio/ConfirmModal.vue'


const title = 'Define tu precio'
const description = 'Establece tu estrategia de precios. Elige el modelo que mejor se adapte a tu negocio.'
const isSelectingSuggestion = ref(false)

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

type UserSearchResult = {
  id: number
  label: string
  suffix: string
  link_instagram: string
  avatar: { src: string }
}

type UserPost = {
  id: string
  thumbnail: string
  shortcode: string
  link_instagram: string
  caption: string | null
  taken_at: string | null
  selected: boolean
}

type UserPostsResponse = {
  posts: UserPost[]
  total: number
  skip: number
  limit: number
}

type SelectedPost = {
  url: string
  title: string
  thumbnail: string
}

type DataModel = {
  email: string
  username: string
  follows: number
  likes: number
  views: number
  comments: number
  user: UserSearchResult | null
  selected_posts: SelectedPost[]
}

const dataModel = ref<DataModel>({
  email: '',
  username: '',
  follows: 0,
  likes: 0,
  views: 0,
  comments: 0,
  user: null,
  selected_posts: []
})

const API_BASE = 'http://localhost:8000'

const proxyImage = (url?: string | null) => {
  if (!url) return ''
  const trimmed = url.trim()
  const proxyPath = '/api/proxy/image?url='
  const isAbsolute = /^https?:\/\//i.test(trimmed)
  if (trimmed.includes(proxyPath)) {
    return isAbsolute ? trimmed : `${API_BASE}${trimmed}`
  }
  return `${API_BASE}${proxyPath}${encodeURIComponent(trimmed)}`
}

// En este flujo NO hacemos un "fetch" extra para validar el username.
// La única fuente de verdad del perfil es el item seleccionado del dropdown
// (/api/users/search/list) que ya viene desde instagrapi.
const selectionError = ref<string | null>(null)

const normalizedUsername = computed(() => {
  const u = (dataModel.value.username || '').trim()
  return u.startsWith('@') ? u.slice(1) : u
})

const canContinueUserInfo = computed(() => {
  return !!dataModel.value.email.trim() && !!dataModel.value.user
})

const postsLoading = ref(false)
const postsModel = ref<UserPostsResponse>({
  posts: [],
  total: 0,
  skip: 0,
  limit: 12
})

const selectedPosts = computed(() => postsModel.value.posts.filter((post) => post.selected))
const canContinuePriceSetting = computed(() => selectedPosts.value.length > 0)

const searchSuggestions = ref<UserSearchResult[]>([])
const searchLoading = ref(false)
const showSuggestions = ref(false)
let searchTimeout: ReturnType<typeof setTimeout> | null = null

const fetchSearchSuggestions = async (query: string): Promise<void> => {
  try {
    const res = await $fetch<UserSearchResult[]>(`${API_BASE}/api/users/search/list`, {
      params: {
        q: query,
        limit: 8
      }
    })
    searchSuggestions.value = res
  } catch (e: any) {
    searchSuggestions.value = []
  } finally {
    searchLoading.value = false
  }
}

const selectSuggestion = async (item: UserSearchResult): Promise<void> => {
  isSelectingSuggestion.value = true

  if (searchTimeout) clearTimeout(searchTimeout)
  searchLoading.value = false

  dataModel.value.username = item.suffix
  dataModel.value.user = item
  selectionError.value = null

  postsModel.value = { posts: [], total: 0, skip: 0, limit: 12 }
  dataModel.value.selected_posts = []

  showSuggestions.value = false
  searchSuggestions.value = []

  await nextTick()
  isSelectingSuggestion.value = false
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

const fetchUserPosts = async (): Promise<void> => {
  if (!dataModel.value.user) {
    toast.add({ title: 'Error', description: 'Primero valida tu usuario de Instagram', color: 'error' })
    return
  }

  postsLoading.value = true
  try {
    const selectedMap = new Map(postsModel.value.posts.map((post) => [post.id, post.selected]))
    const res = await $fetch<UserPostsResponse>(`${API_BASE}/api/users/posts`, {
      params: {
        username: normalizedUsername.value.trim(),
        skip: postsModel.value.skip,
        limit: postsModel.value.limit
      }
    })

    postsModel.value = {
      ...res,
      posts: res.posts.map((post) => ({
        ...post,
        selected: selectedMap.get(post.id) ?? false
      }))
    }
  } catch (e: any) {
    toast.add({ title: 'Error', description: 'No se pudieron cargar los posts', color: 'error' })
  } finally {
    postsLoading.value = false
  }
}

watch(
  () => dataModel.value.username,
  (value) => {
    // Si el usuario edita el input y ya había un "user" seleccionado, lo invalidamos
    if (isSelectingSuggestion.value) return
    if (dataModel.value.user && value.trim() !== dataModel.value.user.suffix) {
      dataModel.value.user = null
	      selectionError.value = null
      postsModel.value = { posts: [], total: 0, skip: 0, limit: 12 }
      dataModel.value.selected_posts = []
    }

    if (searchTimeout) clearTimeout(searchTimeout)

    const query = value.trim().replace(/^@/, "")
    if (query.length < 2) {
      searchSuggestions.value = []
      showSuggestions.value = false
      return
    }

    showSuggestions.value = true
    searchLoading.value = true

    searchTimeout = setTimeout(() => {
      void fetchSearchSuggestions(query)
    }, 400)
  }
)


const verfyUserInfo = async (): Promise<void> => {
  if (!dataModel.value.email.trim()) {
    toast.add({ title: 'Error', description: 'Por favor ingresa tu correo electrónico', color: 'error' })
    return
  }

  // Clave: ahora se valida SOLO por selección del dropdown
  if (!dataModel.value.user) {
    toast.add({
      title: 'Error',
      description: 'Selecciona un perfil de la lista (dropdown) para continuar.',
      color: 'error'
    })
    return
  }

  stepper.value?.next()
  void fetchUserPosts()
}



const verifyForm = async (): Promise<void> => {
  if (selectedPosts.value.length === 0) {
    toast.add({ title: 'Error', description: 'Selecciona al menos un post para continuar', color: 'error' })
    return
  }

  if (totalNumeric.value <= 0) {
    toast.add({ title: 'Error', description: 'Debes seleccionar al menos un servicio', color: 'error' })
    return
  }

  dataModel.value.selected_posts = selectedPosts.value.map((post) => ({
    url: post.link_instagram || '',
    title: post.caption || post.link_instagram || 'Post de Instagram',
    thumbnail: post.thumbnail
  }))
  
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
                    />

                  <div v-if="showSuggestions" class="mt-2 rounded-lg border border-muted bg-background p-2 shadow-sm">
                    <div v-if="searchLoading" class="text-sm text-muted">
                      Buscando perfiles…
                    </div>
                    <div v-else-if="searchSuggestions.length" class="space-y-1">
                      <button
                        v-for="item in searchSuggestions"
                        :key="item.id"
                        type="button"
                        class="flex w-full items-center gap-3 rounded-md p-2 text-left hover:bg-muted"
                        @mousedown.prevent="selectSuggestion(item)"
                      >
	                        <img
	                          v-if="item.avatar?.src"
	                          :src="proxyImage(item.avatar.src)"
                          class="h-8 w-8 rounded-full object-cover"
                          alt="avatar"
                        />
                        <div
                          v-else
                          class="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground"
                        >
                          @
                        </div>
                        <div class="flex-1">
                          <div class="text-sm font-semibold leading-tight">
                            {{ item.label }}
                          </div>
                          <div class="text-xs text-muted">
                            {{ item.suffix }}
                          </div>
                        </div>
                      </button>
                    </div>
                    <div v-else class="text-sm text-muted">
                      No se encontraron resultados.
                    </div>
                  </div>

				  <div class="mt-3">
				    <div v-if="selectionError" class="text-sm text-red-500">
				      {{ selectionError }}
				    </div>

				    <UCard v-else-if="dataModel.user" class="mt-2">
				      <div class="flex items-center gap-3">
				        <img
				          v-if="dataModel.user?.avatar?.src"
				          :src="proxyImage(dataModel.user.avatar.src)"
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
				            {{ dataModel.user.label }}
                    <span class="text-xs text-muted">
                      ({{ dataModel.user.suffix }})
                    </span>
				          </div>
				          <a
				            class="text-sm text-primary underline"
				            :href="dataModel.user.link_instagram"
				            target="_blank"
				            rel="noreferrer"
				          >
				            {{ dataModel.user.link_instagram }}
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
                <div class="space-y-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-base font-semibold">Ultimos posts</h4>
                      <p class="text-sm text-muted">Selecciona los posts en los que quieres trabajar</p>
                    </div>
                    <UButton
                      type="button"
                      label="Recargar"
                      size="sm"
                      variant="outline"
                      :loading="postsLoading"
                      @click="fetchUserPosts"
                    />
                  </div>

                  <div v-if="postsLoading" class="text-sm text-muted">
                    Cargando posts…
                  </div>

                  <div v-else-if="postsModel.posts.length" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <UCard v-for="post in postsModel.posts" :key="post.id">
                      <div class="flex gap-3">
                        <div class="h-20 w-20 overflow-hidden rounded-lg bg-muted">
                          <img
                            v-if="post.thumbnail"
                            :src="proxyImage(post.thumbnail)"
                            :alt="post.caption || 'Post de Instagram'"
                            class="h-full w-full object-cover"
                          />
                        </div>
                        <div class="flex-1">
                          <div class="text-sm font-semibold line-clamp-2">
                            {{ post.caption || 'Post de Instagram' }}
                          </div>
                          <div class="mt-2 flex items-center gap-2 text-xs text-muted">
                            <input
                              v-model="post.selected"
                              type="checkbox"
                              class="h-4 w-4"
                            />
                            <span>Seleccionar</span>
                          </div>
                          <a
                            v-if="post.link_instagram"
                            class="mt-2 block text-xs text-primary underline"
                            :href="post.link_instagram"
                            target="_blank"
                            rel="noreferrer"
                          >
                            Ver post
                          </a>
                        </div>
                      </div>
                    </UCard>
                  </div>
                </div>

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
                    :disabled="!canContinuePriceSetting"
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
