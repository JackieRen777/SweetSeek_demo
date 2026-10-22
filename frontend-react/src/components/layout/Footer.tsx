const Footer = () => (
  <footer className="sweetseek-footer" aria-label="Institution, contact, and filing information">
    <div className="sweetseek-footer__inner">
      <strong>Zhejiang Gongshang University</strong>
      <span className="sweetseek-footer__separator" aria-hidden="true">|</span>
      <span>School of Food Science and Biotechnology</span>
      <span className="sweetseek-footer__separator" aria-hidden="true">|</span>
      <span>
        Contact us:{' '}
        <a href="mailto:hjxie@zjgsu.edu.cn">hjxie@zjgsu.edu.cn</a>
      </span>
    </div>

    <div className="sweetseek-footer__legal">
      <span>Copyright © 2026 SweetSeek Academic Research Platform. All Rights Reserved by FCN Lab.</span>
      <span className="sweetseek-footer__separator" aria-hidden="true">|</span>
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
      >
        豫ICP备2026004112号-1
      </a>
    </div>
  </footer>
);

export default Footer;
