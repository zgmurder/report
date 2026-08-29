<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NForm, NFormItem, NIcon, NInput, useMessage, type FormRules } from 'naive-ui'
import { BarChart3, Bot, DatabaseZap, FileText, LockKeyhole, ShieldCheck, UserRound } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: ['blur', 'input'] }],
  password: [{ required: true, message: '请输入密码', trigger: ['blur', 'input'] }],
}

const redirectPath = computed(() => String(route.query.redirect || '/home/reports'))

async function submitLogin() {
  if (!form.username.trim() || !form.password) {
    message.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.username.trim(), form.password)
    message.success('登录成功')
    router.replace(redirectPath.value)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="hero-panel">
      <div class="brand-area">
        <img class="logo" src="/logo-police.svg" alt="警徽" />
        <div>
          <div class="org">义乌市公安局</div>
          <h1>警情智能辅助分析系统</h1>
        </div>
      </div>

      <div class="hero-copy">
        <p class="eyebrow">Intelligent Police Report Workspace</p>
        <h2>让警情查询、统计研判、报告生成在一个工作台完成</h2>
        <p class="desc">聚合警情数据、智能组件、报告模板与 AI 草稿能力，辅助民警快速形成可校验、可追溯、可导出的警情分析报告。</p>
      </div>

      <div class="feature-grid">
        <div class="feature-card">
          <n-icon :component="DatabaseZap" :size="22" />
          <strong>数据接入</strong>
          <span>部门、警情、模板统一管理</span>
        </div>
        <div class="feature-card">
          <n-icon :component="BarChart3" :size="22" />
          <strong>统计研判</strong>
          <span>趋势、类别、辖区多维分析</span>
        </div>
        <div class="feature-card">
          <n-icon :component="Bot" :size="22" />
          <strong>AI 草稿</strong>
          <span>智能生成后人工确认入库</span>
        </div>
        <div class="feature-card">
          <n-icon :component="FileText" :size="22" />
          <strong>报告工作台</strong>
          <span>结构化报告与编辑器联动</span>
        </div>
      </div>
    </section>

    <section class="login-panel">
      <n-card class="login-card" :bordered="false">
        <div class="card-head">
          <div class="security-badge">
            <n-icon :component="ShieldCheck" :size="18" />
          </div>
          <div>
            <h3>账号登录</h3>
            <p>请使用系统账号进入智能报告工作台</p>
          </div>
        </div>

        <n-form :model="form" :rules="rules" size="large" @keyup.enter="submitLogin">
          <n-form-item path="username" label="用户名">
            <n-input v-model:value="form.username" clearable placeholder="请输入用户名">
              <template #prefix><n-icon :component="UserRound" /></template>
            </n-input>
          </n-form-item>
          <n-form-item path="password" label="密码">
            <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="请输入密码">
              <template #prefix><n-icon :component="LockKeyhole" /></template>
            </n-input>
          </n-form-item>
          <n-button type="primary" block size="large" :loading="loading" class="login-btn" @click="submitLogin">登录系统</n-button>
        </n-form>

        <div class="tips">
          <span>默认开发账号：admin / admin123</span>
          <span>生产环境请通过 .env 修改管理员密码</span>
        </div>
      </n-card>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 480px;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 18%, rgba(24, 144, 255, .22), transparent 30%),
    radial-gradient(circle at 78% 8%, rgba(79, 70, 229, .18), transparent 28%),
    linear-gradient(135deg, #eef7ff 0%, #f7fbff 44%, #e9f3ff 100%);
}

.hero-panel {
  position: relative;
  padding: 56px 64px;
  color: #102033;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.hero-panel::before,
.hero-panel::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
}

.hero-panel::before {
  width: 540px;
  height: 540px;
  left: -170px;
  bottom: -210px;
  background: linear-gradient(135deg, rgba(24, 144, 255, .22), rgba(24, 144, 255, 0));
}

.hero-panel::after {
  width: 360px;
  height: 360px;
  right: 7%;
  top: 12%;
  border: 1px solid rgba(24, 144, 255, .24);
  box-shadow: inset 0 0 80px rgba(24, 144, 255, .08);
}

.brand-area,
.hero-copy,
.feature-grid {
  position: relative;
  z-index: 1;
}

.brand-area {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  width: 58px;
  height: 58px;
  filter: drop-shadow(0 12px 18px rgba(24, 144, 255, .2));
}

.org {
  font-size: 14px;
  color: #5b6b7f;
  letter-spacing: .1em;
}

h1 {
  margin: 4px 0 0;
  font-size: 24px;
  letter-spacing: .04em;
}

.hero-copy {
  max-width: 720px;
  margin-top: 80px;
}

.eyebrow {
  margin: 0 0 18px;
  color: #1890ff;
  font-weight: 700;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.hero-copy h2 {
  margin: 0;
  font-size: clamp(34px, 5vw, 58px);
  line-height: 1.12;
  letter-spacing: -.04em;
}

.desc {
  max-width: 660px;
  margin: 22px 0 0;
  color: #51657b;
  font-size: 17px;
  line-height: 1.85;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 56px;
}

.feature-card {
  min-height: 118px;
  padding: 18px;
  border: 1px solid rgba(24, 144, 255, .16);
  border-radius: 20px;
  background: rgba(255, 255, 255, .64);
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 42px rgba(24, 75, 120, .08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-card .n-icon {
  color: #1890ff;
}

.feature-card strong {
  font-size: 15px;
}

.feature-card span {
  color: #65758b;
  font-size: 13px;
  line-height: 1.5;
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: rgba(255, 255, 255, .42);
  backdrop-filter: blur(22px);
  border-left: 1px solid rgba(255, 255, 255, .8);
}

.login-card {
  width: 100%;
  max-width: 396px;
  border-radius: 28px;
  box-shadow: 0 30px 80px rgba(16, 44, 84, .16);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
}

.security-badge {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #1890ff, #2f54eb);
  box-shadow: 0 14px 26px rgba(24, 144, 255, .28);
}

.card-head h3 {
  margin: 0;
  font-size: 24px;
}

.card-head p {
  margin: 4px 0 0;
  color: #7a8798;
}

.login-btn {
  height: 46px;
  margin-top: 4px;
  border-radius: 12px;
  font-weight: 600;
}

.tips {
  margin-top: 20px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f5f9ff;
  color: #6b7c91;
  font-size: 12px;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
}

@media (max-width: 980px) {
  .login-page { grid-template-columns: 1fr; }
  .hero-panel { min-height: 54vh; padding: 36px 24px; }
  .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .login-panel { padding: 24px; border-left: 0; }
}
</style>
