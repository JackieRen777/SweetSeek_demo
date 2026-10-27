import type { QADomain } from '../../lib/usageAnalytics';

export interface ResearchQAConfig {
  analyticsDomain: QADomain;
  apiBase: string;
  title: string;
  subtitle: string;
  placeholder: string;
  ariaLabel: string;
  welcomeTestId: string;
  presetQuestions: string[];
  compactMobileTitle?: boolean;
}

export const encapsulationQAConfig: ResearchQAConfig = {
  analyticsDomain: 'encapsulation',
  apiBase: '/api/encapsulation',
  title: 'Explore encapsulation science',
  subtitle: 'from precise encapsulation to targeted release',
  placeholder: 'Ask anything about encapsulation research',
  ariaLabel: 'Encapsulation question',
  welcomeTestId: 'encapsulation-welcome',
  presetQuestions: [
    '哪些壁材可以提高包埋效率？',
    '喷雾干燥如何影响生物活性物质的稳定性？',
    '食品递送系统中的释放行为受哪些因素控制？',
  ],
};
