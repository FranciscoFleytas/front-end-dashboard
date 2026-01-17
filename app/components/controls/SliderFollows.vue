<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import noUiSlider from 'nouislider'
import 'nouislider/distribute/nouislider.css'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100000 },
  step: { type: Number, default: 1 },
  marks: { type: Array as () => (number | { value: number; label?: string })[], default: () => [] },
  showLabels: { type: Boolean, default: true }
})
const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const slider = ref<HTMLElement | null>(null)
let sliderInstance: any = null

const normalizeMarks = () =>
  (props.marks || [])
    .map(m => (typeof m === 'number' ? m : m.value))
    .filter(v => typeof v === 'number' && v >= props.min && v <= props.max)

const abbreviate = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(n % 1000000 === 0 ? 0 : 1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'k'
  return String(n)
}

const create = async () => {
  if (!slider.value) return

  const pipValues = normalizeMarks()

  const options: any = {
    start: props.modelValue,
    connect: true,
    step: props.step,
    range: { min: props.min, max: props.max },
    tooltips: {
      to: (v: number) => abbreviate(Math.round(Number(v)))
    }
  }

  if (pipValues.length > 0) {
    options.pips = {
      mode: 'values',
      values: pipValues,
      density: 4,
      format: {
        to: (v: number) => abbreviate(Math.round(Number(v)))
      }
    }
  }

  sliderInstance = noUiSlider.create(slider.value as HTMLElement, options)

  sliderInstance.on('update', (values: any[]) => {
    const v = Math.round(Number(values[0]))
    emit('update:modelValue', v)
  })

  if (pipValues.length > 0) {
    // wait a tick so pips are rendered
    await nextTick()
    setTimeout(() => {
      const pipEls = (slider.value as HTMLElement).querySelectorAll('.noUi-value')
      pipEls.forEach(el => {
        const text = el.textContent?.trim() || ''
        const match = pipValues.find(v => abbreviate(v) === text)
        if (match !== undefined) {
          ;(el as HTMLElement).style.cursor = 'pointer'
          el.setAttribute('tabindex', '0')
          el.addEventListener('click', () => sliderInstance.set(match))
          el.addEventListener('keydown', (ev: Event) => {
            const kev = ev as KeyboardEvent
            if (kev.key === 'Enter' || kev.key === ' ') {
              ev.preventDefault()
              sliderInstance.set(match)
            }
          })
        }
      })
    }, 30)
  }
}

onMounted(() => {
  create()
})

watch(
  () => props.modelValue,
  nv => {
    if (sliderInstance) sliderInstance.set(nv)
  }
)

// If core bounds or marks change, recreate the slider
watch([() => props.min, () => props.max, () => props.marks], async () => {
  if (sliderInstance && sliderInstance.destroy) sliderInstance.destroy()
  sliderInstance = null
  await nextTick()
  create()
})

onBeforeUnmount(() => {
  if (sliderInstance && sliderInstance.destroy) sliderInstance.destroy()
})
</script>

<template>
  <div>
    <div ref="slider" />
  </div>
</template>

<style scoped>
/* subtle visual overrides to match project theme */
.noUi-target {
  background: linear-gradient(90deg, rgba(0,193,106,0.06), rgba(6,182,212,0.04));
  height: 6px;
  border-radius: 9999px;
}
.noUi-connect {
  background: linear-gradient(90deg, var(--color-green-500), var(--color-cyan-400));
  height: 6px;
  border-radius: 9999px;
}
.noUi-handle {
  width: 20px;
  height: 20px;
  top: -7px;
  background: #fff;
  border: 3px solid var(--color-green-500);
  box-shadow: 0 6px 16px rgba(12,12,12,0.12);
}
.noUi-tooltip {
  background: var(--color-green-500);
  color: white;
  border-radius: 6px;
}
.noUi-value {
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}
</style>
