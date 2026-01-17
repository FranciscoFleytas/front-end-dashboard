<template>
  <div class="w-full py-2.5">
    <USlider
      v-model="currentIndex"
      :min="0"
      :max="ticks.length - 1"
      :step="1"
      class="w-full cursor-pointer"
    />
  </div>
  <!-- Range Input -->
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface Props {
  modelValue: number
  min: number
  max: number
  step?: number
  ticks?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  step: 1,
  ticks: () => []
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const currentIndex = ref(0)

const updateIndex = () => {
  const index = props.ticks.indexOf(props.modelValue)
  currentIndex.value = index !== -1 ? index : 0
}

watch(() => props.modelValue, updateIndex, { immediate: true })

watch(currentIndex, (newIndex) => {
  emit('update:modelValue', props.ticks[newIndex]!)
})
</script>
