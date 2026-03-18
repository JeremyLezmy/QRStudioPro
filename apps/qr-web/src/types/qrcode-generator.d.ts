declare module 'qrcode-generator' {
  interface QRCode {
    addData(data: string): void;
    make(): void;
    getModuleCount(): number;
    isDark(row: number, col: number): boolean;
  }

  type QRErrorCorrectionLevel = 'L' | 'M' | 'Q' | 'H';

  function qrcode(typeNumber: number, errorCorrectionLevel: QRErrorCorrectionLevel): QRCode;

  export default qrcode;
}
