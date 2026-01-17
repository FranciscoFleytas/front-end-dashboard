<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import noUiSlider from 'nouislider'
import 'nouislider/distribute/nouislider.css'

const props = defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },
  marks: { type: Array as () => (number | { value: number, label?: string })[], default: () => [] },
  showLabels: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue'])

const slider = ref<HTMLElement | null>(null)
let sliderInstance: any = null

const normalizeMarksValues = () => {
  return (props.marks || []).map(m => (typeof m === 'number' ? m : m.value))
}

onMounted(() => {
  if (!slider.value) return

  const pipValues = normalizeMarksValues()

  const options: any = {
    start: props.modelValue,
    connect: [true, false],
    step: props.step,
    range: { min: props.min, max: props.max },
    tooltips: true
  }

  if (pipValues.length > 0) {
    options.pips = {
      mode: 'values',
      values: pipValues,
      density: 4
    }
  }

  sliderInstance = noUiSlider.create(slider.value as HTMLElement, options)

  sliderInstance.on('update', (values: any[]) => {
    const v = Math.round(Number(values[0]))
    emit('update:modelValue', v)
  })
})

watch(() => props.modelValue, (nv) => {
  if (sliderInstance) {
    sliderInstance.set(nv)
  }
})

onBeforeUnmount(() => {
  if (sliderInstance && sliderInstance.destroy) sliderInstance.destroy()
})
</script>

<template>
  <div>
    <div ref="slider"></div>
  </div>
</template>

<style scoped>
/* tiny overrides to match template */
.noUi-target {
  background: linear-gradient(90deg, rgba(0,193,106,0.08), rgba(6,182,212,0.06));
  height: 6px;
  border-radius: 9999px;
}
.noUi-handle {
  width: 20px;
  height: 20px;
  top: -7px;
  background: #fff;
  border: 3px solid var(--color-green-500);
  box-shadow: 0 2px 6px rgba(12,12,12,0.16);
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
