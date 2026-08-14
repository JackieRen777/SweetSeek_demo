import type { ResearchQAConfig } from '../encapsulation/researchQAConfig';

export const proteoglycanQAConfig: ResearchQAConfig = {
  apiBase: '/api/proteoglycan',
  title: 'Explore protein-polysaccharide science',
  subtitle: 'from molecular interactions to functional systems',
  placeholder: 'Ask anything about protein-polysaccharide systems',
  ariaLabel: 'Proteoglycan question',
  welcomeTestId: 'proteoglycan-welcome',
  compactMobileTitle: true,
  presetQuestions: [
    '蛋白质与多糖通过哪些相互作用形成复合物？',
    'pH、离子强度和热处理如何影响蛋白-多糖体系的稳定性？',
    '如何设计兼具乳化、凝胶和递送功能的蛋白-多糖体系？',
  ],
};
