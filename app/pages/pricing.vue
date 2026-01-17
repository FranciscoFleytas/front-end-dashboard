<script setup lang="ts">
const title = 'Pricing'
const description = 'Choose the perfect plan for your business. No hidden fees.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description
})

const isYearly = ref('0')

const plans = [
  {
    name: 'Starter Pack',
    description: 'Ideal para perfiles personales',
    price: '$650',
    period: '/7 días',
    features: [
      'Meta de 10k Seguidores',
      'Aumento de engagement (5% - 8%)',
      'Likes y vistas en 4 posts',
      '25 comentarios orgánicos por post',
      'Validación social inmediata'
    ],
    highlighted: false
  },
  {
    name: 'Standard Pack',
    description: 'Para quienes desean acelerar su crecimiento',
    price: '$1,200',
    period: '/15 días',
    features: [
      'Meta de 25k Seguidores',
      'Aumento de engagement (8% - 10%)',
      'Likes y vistas en 10 posts',
      '35 comentarios orgánicos por post',
      'Reposicionamiento digital',
      'Soporte prioritario'
    ],
    highlighted: false
  },
  {
    name: 'Premium Pack',
    description: 'Para perfiles de alto impacto',
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

const faqs = [
  {
    question: 'Can I change plans anytime?',
    answer: 'Yes, you can upgrade or downgrade your plan at any time. Changes will be reflected in your next billing cycle.'
  },
  {
    question: 'Do you offer a free trial?',
    answer: 'Yes, we offer a 14-day free trial on all paid plans. No credit card required.'
  },
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards (Visa, Mastercard, American Express) and PayPal.'
  },
  {
    question: 'Is there a refund policy?',
    answer: 'Yes, we offer a 30-day money-back guarantee. If you\'re not satisfied, we\'ll refund your payment.'
  },
  {
    question: 'Can I cancel my subscription?',
    answer: 'Yes, you can cancel your subscription at any time from your account settings.'
  },
  {
    question: 'Do you offer discounts for non-profits?',
    answer: 'Yes, we offer special pricing for non-profit organizations and educational institutions. Contact us for more info.'
  }
]

const logos = [
  'i-simple-icons-aws',
  'i-simple-icons-heroku',
  'i-simple-icons-netlify',
  'i-simple-icons-vercel',
  'i-simple-icons-cloudflare',
  'i-simple-icons-digitalocean'
]
</script>

<template>
  <div>
    <UPageHero
      :title="title"
      :description="description"
    >
    </UPageHero>

    <UContainer>
      <UPricingPlans scale>
        <UPricingPlan
          v-for="(plan, index) in plans"
          :key="index"
          :name="plan.name"
          :description="plan.description"
          :price="plan.price"
          :billing-cycle="plan.period"
          :features="plan.features"
          :highlighted="plan.highlighted"
          :to="plan.highlighted ? '/signup' : '#'"
        />
      </UPricingPlans>
    </UContainer>

    <UPageSection>
      <UPageLogos>
        <UIcon
          v-for="icon in logos"
          :key="icon"
          :name="icon"
          class="w-12 h-12 flex-shrink-0 text-muted"
        />
      </UPageLogos>
    </UPageSection>

    <UPageSection
      title="Frequently Asked Questions"
      description="Everything you need to know about our pricing."
    >
      <UAccordion
        :items="faqs.map((faq, index) => ({ label: faq.question, defaultOpen: index === 0, content: faq.answer }))"
        :unmount-on-hide="false"
        type="multiple"
        class="max-w-3xl mx-auto"
        :ui="{
          trigger: 'text-base text-highlighted',
          body: 'text-base text-muted'
        }"
      />
    </UPageSection>

    <USeparator />

    <UPageCTA
      title="Still have questions?"
      description="Our team is here to help. Contact us and we\'ll get back to you within 24 hours."
      :links="[
        { label: 'Contact support', to: '/dashboard' }
      ]"
      variant="naked"
      class="overflow-hidden"
    />
  </div>
</template>
