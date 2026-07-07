<template>
  <section class="search-page grid min-h-0 bg-[#090b0f] text-[#eef2f7]">
    <SearchFilters
      v-model:query="query"
      v-model:face-min-similarity="faceMinSimilarity"
      :selected-image-name="selectedImageName"
      :selected-image-preview-url="selectedImagePreviewUrl"
      :is-searching-text="isSearchingText"
      :is-searching-face="isSearchingFace"
      :error-message="errorMessage"
      @text-search="submitTextSearch"
      @image-search="submitFaceSearch"
    />
    <SearchResults
      :text-results="textResults"
      :face-results="faceResults"
      :selected-image-name="selectedImageName"
      :is-searching-face="isSearchingFace"
      @clear="clearResults"
    />
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";

import SearchFilters from "../components/search/SearchFilters.vue";
import SearchResults from "../components/search/SearchResults.vue";
import {
  searchFaces,
  searchPeople,
  type FaceSearchResult,
  type PeopleSearchResult
} from "../api";

/** 搜索输入框中的关键词。 */
const query = ref("");
/** 最近一次以图搜图选择的文件名。 */
const selectedImageName = ref("");
/** 最近一次以图搜图选择的本地预览 URL。 */
const selectedImagePreviewUrl = ref("");
/** 文本人物搜索结果。 */
const textResults = ref<PeopleSearchResult[]>([]);
/** 人脸图片搜索结果。 */
const faceResults = ref<FaceSearchResult[]>([]);
/** 以图搜图的手动相似度阈值。 */
const faceMinSimilarity = ref(0.55);
/** 文本搜索请求是否进行中。 */
const isSearchingText = ref(false);
/** 图片搜索请求是否进行中。 */
const isSearchingFace = ref(false);
/** 搜索页展示的错误消息。 */
const errorMessage = ref("");

/** 提交关键词人物搜索并更新结果列表。 */
async function submitTextSearch() {
  isSearchingText.value = true;
  errorMessage.value = "";
  try {
    textResults.value = await searchPeople(query.value.trim(), 80);
  } catch {
    errorMessage.value = "搜索失败，请检查后端是否运行。";
  } finally {
    isSearchingText.value = false;
  }
}

/** 提交人脸图片搜索并记录图片文件名。 */
async function submitFaceSearch(file: File) {
  selectedImageName.value = file.name;
  replaceImagePreview(file);
  errorMessage.value = "";
  isSearchingFace.value = true;
  try {
    faceResults.value = await searchFaces(file, 10, faceMinSimilarity.value);
  } catch {
    errorMessage.value = "以图搜图失败，请确认图片里有人脸且人物库已生成。";
  } finally {
    isSearchingFace.value = false;
  }
}

/** 清空文本和图片两类搜索结果。 */
function clearResults() {
  query.value = "";
  selectedImageName.value = "";
  revokeImagePreview();
  textResults.value = [];
  faceResults.value = [];
  errorMessage.value = "";
}

/** 替换上传图片预览，避免重复创建 object URL。 */
function replaceImagePreview(file: File) {
  revokeImagePreview();
  selectedImagePreviewUrl.value = URL.createObjectURL(file);
}

/** 释放上传图片预览占用的本地 URL。 */
function revokeImagePreview() {
  if (!selectedImagePreviewUrl.value) return;
  URL.revokeObjectURL(selectedImagePreviewUrl.value);
  selectedImagePreviewUrl.value = "";
}

onBeforeUnmount(revokeImagePreview);
</script>

<style scoped>
.search-page {
  grid-template-columns: 320px minmax(0, 1fr);
}

@media (max-width: 900px) {
  .search-page {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}
</style>
