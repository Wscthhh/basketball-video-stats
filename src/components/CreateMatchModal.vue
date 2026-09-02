<script setup lang="ts">
import { Check, Plus, X } from 'lucide-vue-next'
import type { CreateMatchDraft } from '../types'

defineProps<{ busy: boolean }>()
defineEmits<{ close: []; submit: [] }>()
const draft = defineModel<CreateMatchDraft>('draft', { required: true })

const commonColors = [
  { name: '黑色', value: '#171A18' },
  { name: '白色', value: '#F4F5F0' },
  { name: '红色', value: '#D73A3A' },
  { name: '蓝色', value: '#3267D6' },
  { name: '绿色', value: '#2F9E62' },
  { name: '黄色', value: '#F2C94C' },
  { name: '橙色', value: '#E98232' },
  { name: '紫色', value: '#8B5FC7' },
]
</script>

<template>
  <div class="modal-layer" @click.self="$emit('close')">
    <section class="modal">
      <div class="modal-header"><div><span class="panel-kicker"><Plus :size="13" /> NEW MATCH</span><h2>创建比赛</h2></div><button class="icon-button dark" type="button" title="关闭" @click="$emit('close')"><X :size="18" /></button></div>
      <div class="form-grid">
         <label><span>比赛日期</span><input v-model="draft.playedAt" type="datetime-local" /></label>
        <label><span>比赛场地</span><input v-model="draft.venue" /></label><span></span>
        <label><span>主队名称 *</span><input v-model="draft.homeName" /></label>
        <div class="match-color-field"><span>主队颜色</span><div class="match-color-picker"><input v-model="draft.homeColor" type="color" aria-label="自定义主队颜色" /><div class="common-color-list"><button v-for="color in commonColors" :key="`home-${color.value}`" type="button" :class="{ selected: draft.homeColor.toUpperCase() === color.value }" :style="{ '--match-color': color.value }" :title="color.name" :aria-label="`选择主队${color.name}`" @click="draft.homeColor = color.value"></button></div></div></div>
        <label><span>客队名称 *</span><input v-model="draft.awayName" /></label>
        <div class="match-color-field"><span>客队颜色</span><div class="match-color-picker"><input v-model="draft.awayColor" type="color" aria-label="自定义客队颜色" /><div class="common-color-list"><button v-for="color in commonColors" :key="`away-${color.value}`" type="button" :class="{ selected: draft.awayColor.toUpperCase() === color.value }" :style="{ '--match-color': color.value }" :title="color.name" :aria-label="`选择客队${color.name}`" @click="draft.awayColor = color.value"></button></div></div></div>
      </div>
      <div class="modal-footer"><span>一期只管理球队片段归属</span><button class="button button-acid" type="button" :disabled="busy" @click="$emit('submit')"><Check :size="16" /> 创建并进入</button></div>
    </section>
  </div>
</template>
