<script setup lang="ts">
import { Check, Plus, X } from 'lucide-vue-next'
import type { CreateMatchDraft } from '../types'

defineProps<{ busy: boolean }>()
defineEmits<{ close: []; submit: [] }>()
const draft = defineModel<CreateMatchDraft>('draft', { required: true })
</script>

<template>
  <div class="modal-layer" @click.self="$emit('close')">
    <section class="modal">
      <div class="modal-header"><div><span class="panel-kicker"><Plus :size="13" /> NEW MATCH</span><h2>创建比赛</h2></div><button class="icon-button dark" type="button" title="关闭" @click="$emit('close')"><X :size="18" /></button></div>
      <div class="form-grid">
        <label><span>比赛名称 *</span><input v-model="draft.name" /></label>
        <label><span>比赛日期</span><input v-model="draft.playedAt" type="datetime-local" /></label>
        <label><span>比赛场地</span><input v-model="draft.venue" /></label><span></span>
        <label><span>主队名称 *</span><input v-model="draft.homeName" /></label>
        <label><span>主队颜色</span><input v-model="draft.homeColor" type="color" /></label>
        <label><span>客队名称 *</span><input v-model="draft.awayName" /></label>
        <label><span>客队颜色</span><input v-model="draft.awayColor" type="color" /></label>
      </div>
      <div class="modal-footer"><span>一期只管理球队片段归属</span><button class="button button-acid" type="button" :disabled="busy" @click="$emit('submit')"><Check :size="16" /> 创建并进入</button></div>
    </section>
  </div>
</template>
