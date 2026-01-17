<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'

const emit = defineEmits<{ close: [boolean] }>()

const condiciones = ref(false)
const error = ref('')
const checkboxRef = ref()

watch(condiciones, (newVal) => {
  if (newVal) {
    error.value = ''
  }
})

const handleConfirm = () => {
  if (!condiciones.value) {
    error.value = 'Debes aceptar las condiciones para continuar.'
    nextTick(() => {
      checkboxRef.value?.focus()
    })
    return
  }

  emit('close', true)
}
</script>

<template>
  <UModal
    :close="{ onClick: () => emit('close', false) }"
    :title="`Confirmar el pedido`"
  >
    <template #body>
      <div>
        <p class="mb-4">
          Es posible que demore entre 24 y 48 horas hábiles para que se procese tu pedido.
        </p>
        <UCheckbox
          ref="checkboxRef"
          v-model="condiciones"
          autofocus="true"
          label="Acepto que puede haber hasta 48 horas hábiles de demora en el procesamiento."
          required
        />
        <p
          v-if="error"
          class="text-red-500 text-sm mt-2"
        >
          {{ error }}
        </p>
      </div>
    </template>
    <template #footer>
      <div class="flex gap-2">
        <UButton
          color="error"
          label="Cancelar"
          variant="outline"
          @click="emit('close', false)"
        />
        <UButton
          label="Confirmar"
          @click="handleConfirm"
        />
      </div>
    </template>
  </UModal>
</template>
