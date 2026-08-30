<script setup lang="ts">
import { CloudUpload, Upload, X } from 'lucide-vue-next'

defineProps<{ files: File[]; busy: boolean }>()
const emit = defineEmits<{ close: []; upload: []; selectFiles: [files: File[]] }>()

function selectFiles(event: Event) {
  const input = event.target as HTMLInputElement
  emit('selectFiles', Array.from(input.files ?? []))
}
</script>

<template>
  <div class="modal-layer" @click.self="$emit('close')">
    <section class="modal">
      <div class="modal-header"><div><span class="panel-kicker"><Upload :size="13" /> LOCAL INGEST</span><h2>导入比赛片段</h2></div><button class="icon-button dark" type="button" title="关闭" @click="$emit('close')"><X :size="18" /></button></div>
      <label class="file-picker"><CloudUpload :size="23" /><strong>选择本地视频</strong><span>支持 MP4、MOV、M4V、WebM，可多选</span><input type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" multiple @change="selectFiles" /></label>
      <div class="modal-footer"><span>{{ files.length }} 个文件待上传</span><button class="button button-acid" type="button" :disabled="busy || !files.length" @click="$emit('upload')"><CloudUpload :size="16" /> 上传并自动分析</button></div>
    </section>
  </div>
</template>
