<script setup lang="ts">
const title = '¡Hacé que tu perfil explote!'
const description = 'Impulsa el crecimiento de tu Instagram con resultados garantizados. Seguidores e interacciones reales, sin procesos complejos y con entrega inmediata. Obtén la relevancia que tu perfil necesita de forma segura.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description
})

const features = [
  {
    title: 'Resultados de alta calidad',
    description: 'Obtén seguidores e interacciones reales diseñados para mejorar la autoridad de tu perfil. Proyecta una imagen profesional y destaca frente a la competencia desde el primer momento',
    icon: 'i-lucide-user-check'
  },
  {
    title: 'Entrega inmediata y segura',
    description: 'Sistema automatizado con activación al instante tras confirmar tu pedido. No solicitamos contraseñas ni datos sensibles, garantizando la total privacidad y seguridad de tu cuenta.',
    icon: 'i-lucide-shield'
  },
  {
    title: 'Soporte personalizado',
    description: 'Asistencia técnica dedicada para resolver tus dudas y asegurar que tu experiencia sea satisfactoria. Garantía de reposición en todos nuestros servicios para tu mayor tranquilidad.',
    icon: 'i-lucide-headset'
  }
]

const testimonials = [
  {
    quote: 'Este servicio transformó mi perfil de Instagram. La calidad de seguidores e interacciones es excepcional - todo funciona perfectamente con resultados reales.',
    user: {
      name: 'María González',
      role: 'Influencer Lifestyle'
    }
  },
  {
    quote: 'Lanzamos nuestra marca en 2 semanas en lugar de 2 meses. Los flujos de crecimiento y engagement nos ahorraron incontables horas.',
    user: {
      name: 'Carlos Rodríguez',
      role: 'Emprendedor Digital'
    }
  },
  {
    quote: 'Puntuaciones perfectas de engagement. Nuestro alcance y retención mejoraron dramáticamente con este servicio.',
    user: {
      name: 'Ana López',
      role: 'Creadora de Contenido'
    }
  },
  {
    quote: 'El sistema de crecimiento con métricas es brillante. Mantenemos consistencia en nuestro branding digital.',
    user: {
      name: 'Pedro Martínez',
      role: 'Fotógrafo Profesional'
    }
  }
]
/*
const pricingPlans = [
  {
    name: 'Posicionamiento Base',
    price: '$650',
    period: '/mes',
    features: [
      'Resultado: Validación social y relevancia orgánica [cite: 43, 44]',
      'Auditoría inicial de perfil y competencia [cite: 15]',
      'Asesoría "Algoritmo sin humo" y lectura de Insights',
      'Sistema de hashtags y checklist anti-shadowban',
      'Calendario mensual con pilares de contenido',
      'Soporte en 4 posts: +5% a 8% engagement [cite: 48, 49]',
      '~25 comentarios orgánicos por publicación [cite: 50]',
      'Reporte mensual de rendimiento y optimización'
    ]
  },
  {
    name: 'Aceleración de Relevancia',
    price: '$1,200',
    period: '/mes',
    features: [
      'Resultado: Referencia de nicho y más conversaciones [cite: 80, 103]',
      'Incluye todo el Plan de Posicionamiento Base',
      '2 sesiones estratégicas de optimización mensual',
      'Arquitectura de contenido para conversión y DMs [cite: 94]',
      'Mapa de autoridad para reposicionamiento digital [cite: 91, 93]',
      'Soporte en 10 posts: +8% a 10% engagement [cite: 52, 53]',
      '~35 comentarios orgánicos por publicación [cite: 55]',
      'A/B testing de ganchos y formatos de alto alcance'
    ]
  },
  {
    name: 'Dominio y Autoridad',
    price: '$2,000',
    period: '/mes',
    features: [
      'Resultado: Máximo estatus y autoridad percibida [cite: 93, 114]',
      'Incluye todo el Plan de Aceleración de Relevancia',
      'Sesión semanal de dirección creativa (4/mes) [cite: 12]',
      'Sistema anti-shadowban avanzado y recuperación',
      'Optimización integral para conversión (Bio/Highlights)',
      'Soporte en 23 posts: +10% a 15% engagement [cite: 57, 59]',
      '~60-70 comentarios orgánicos por publicación [cite: 60]',
      'Dashboard de KPIs: Alcance, retención y conversiones'
    ],
    highlighted: false
  }
]
*/

const pricingPlans = [
  {
    name: 'Starter Pack',
    price: '$650',
    period: '/7 días',
    features: [
      'Meta de 10k Seguidores',
      'Aumento de engagement (5% - 8%)',
      'Likes y vistas en 4 posts',
      '25 comentarios orgánicos por post',
      'Validación social inmediata'
    ]
  },
  {
    name: 'Standard Pack',
    price: '$1,200',
    period: '/15 días',
    features: [
      'Meta de 25k Seguidores',
      'Aumento de engagement (8% - 10%)',
      'Likes y vistas en 10 posts',
      '35 comentarios orgánicos por post',
      'Reposicionamiento digital',
      'Soporte prioritario'
    ]
  },
  {
    name: 'Premium Pack',
    price: '$2,000',
    period: '/30 días',
    features: [
      'Meta de 55k Seguidores',
      'Aumento de engagement (10% - 15%)',
      'Likes y vistas en 23 posts',
      'Hasta 70 comentarios por post',
      'Autoridad de marca consolidada',
      'Refuerzo de visibilidad premium'
    ],
    highlighted: false
  }
]
</script>

<template>
  <div>
    <!-- Hero Section -->
    <UPageHero
      :title="title"
      :description="description"
      :links="[
        { label: 'Impulsar mi perfil', to: '/pricing' },
        { label: 'Poner mi precio', to: '/poner-precio', variant: 'outline'}
      ]"
    />

    <!-- Features Section -->
    <UPageSection
      title="Todo lo que necesitas"
      description="Impulsa tu presencia digital de forma rápida y segura. Enfócate en tu contenido mientras nosotros nos encargamos de tu crecimiento"
      class="bg-elevated/50"
    >
      <UPageGrid>
        <UPageCard
          v-for="(feature, index) in features"
          :key="index"
          :title="feature.title"
          :description="feature.description"
          :icon="feature.icon"
          variant="subtle"
          spotlight
        />
      </UPageGrid>
    </UPageSection>

    <!-- Pricing Section -->
    <UPageSection
      title="Precios Simples y Transparentes"
      description="Elige el plan que mejor se adapte a tu perfil de Instagram."
    >
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        <UPageCard
          v-for="(plan, index) in pricingPlans"
          :key="index"
          :title="plan.name"
          :description="plan.period"
          variant="subtle"
          :class="{ 'ring-2 ring-primary': plan?.highlighted }"
        >
          <template #header>
            <p class="text-4xl font-bold">
              {{ plan.price }}
              <span class="text-sm font-normal text-muted">{{ plan.period }}</span>
            </p>
          </template>

          <ul class="space-y-2 mb-6">
            <li v-for="(feature, fIndex) in plan.features" :key="fIndex" class="flex items-center gap-2">
              <UIcon name="i-lucide-check" class="text-success size-4" />
              <span class="text-sm">{{ feature }}</span>
            </li>
          </ul>

          <UButton
            :label="plan?.highlighted ? 'Comenzar ahora' : 'Elegir plan'"
            :variant="plan?.highlighted ? 'solid' : 'outline'"
            block
            :to="plan?.highlighted ? '/signup' : '/pricing'"
          />
        </UPageCard>
      </div>
    </UPageSection>

    <!-- Testimonials Section -->
    <UPageSection
      title="Confiado por Creadores de Contenido"
      description="Únete a miles de creadores impulsando su presencia en Instagram."
      class="bg-elevated/50"
    >
      <UPageColumns class="xl:columns-4">
        <UPageCard
          v-for="(testimonial, index) in testimonials"
          :key="index"
          variant="subtle"
          :description="testimonial.quote"
          :ui="{ description: 'before:content-[open-quote] after:content-[close-quote]' }"
        >
          <template #footer>
            <UUser
              :name="testimonial.user.name"
              :description="testimonial.user.role"
              size="lg"
            />
          </template>
        </UPageCard>
      </UPageColumns>
    </UPageSection>

    <!-- CTA Section -->
    <USeparator />

    <UPageCTA
      title="¿Listo para hacer crecer tu perfil?"
      description="Únete a miles de creadores impulsando tu presencia en Instagram. Comienza hoy mismo."
      :links="[
        { label: 'Impulsar ahora', to: '/pricing' },
        { label: 'Poner mi precio', to: '/poner-precio' }
      ]"
      variant="naked"
      class="overflow-hidden"
    />
  </div>
</template>
