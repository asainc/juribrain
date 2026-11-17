/** Contexto opcional usado exclusivamente para complementar perguntas do chat corporativo. */
export type ChatReferenceType = 'gcpj' | 'numero_cnj' | 'numero_conectajur';

export type ChatReferenceOption = {
  value: ChatReferenceType;
  label: string;
  promptLabel: string;
};

export const CHAT_REFERENCE_OPTIONS: readonly ChatReferenceOption[] = [
  {value: 'gcpj', label: 'GCPJ', promptLabel: 'gcpj'},
  {value: 'numero_cnj', label: 'Número CNJ', promptLabel: 'número cnj'},
  {value: 'numero_conectajur', label: 'Número ConectaJur', promptLabel: 'número conectajur'},
];

export const MAX_CHAT_REFERENCE_LENGTH = 80;
export const MAX_CHAT_PROMPT_LENGTH = 8000;

/**
 * Constrói a pergunta efetivamente transmitida à API Q&A.
 * O identificador é opcional e não altera o texto original salvo no histórico visual.
 * Não padronizamos o formato numérico: a validação oficial pertence ao sistema de origem.
 */
export function buildContextualChatPrompt(
  question: string,
  referenceType: ChatReferenceType,
  referenceValue: string,
): string {
  const normalizedQuestion = question.trim();
  if (!normalizedQuestion) throw new Error('Digite uma pergunta antes de enviar.');

  // O campo de referência não pode introduzir linhas ou caracteres de controle no prompt.
  if (/[\u0000-\u001f\u007f]/.test(referenceValue)) {
    throw new Error('O identificador deve conter apenas uma linha, sem caracteres de controle.');
  }
  const normalizedValue = referenceValue.trim();
  if (!normalizedValue) {
    if (normalizedQuestion.length > MAX_CHAT_PROMPT_LENGTH) {
      throw new Error('A pergunta deve ter até 8.000 caracteres.');
    }
    return normalizedQuestion;
  }
  if (normalizedValue.length > MAX_CHAT_REFERENCE_LENGTH) {
    throw new Error(`O identificador deve ter até ${MAX_CHAT_REFERENCE_LENGTH} caracteres.`);
  }
  // Aceita os separadores usuais de identificadores, sem assumir um formato corporativo não confirmado.
  if (!/^[\p{L}\p{N}][\p{L}\p{N}._/:\-]*$/u.test(normalizedValue)) {
    throw new Error('Use apenas letras, números, ponto, hífen, barra, sublinhado ou dois-pontos no identificador.');
  }

  const option = CHAT_REFERENCE_OPTIONS.find(item => item.value === referenceType);
  if (!option) throw new Error('Selecione um tipo de identificador válido.');

  // O complemento é inserido antes da pontuação final para manter perguntas naturais.
  const endPunctuation = normalizedQuestion.match(/[.!?]$/)?.[0] ?? '';
  const baseQuestion = endPunctuation ? normalizedQuestion.slice(0, -1).trimEnd() : normalizedQuestion;
  const outgoingPrompt = `${baseQuestion} do ${option.promptLabel} ${normalizedValue}${endPunctuation}`;
  // O contrato Q&A limita a pergunta total a 8.000 caracteres, incluindo o contexto.
  if (outgoingPrompt.length > MAX_CHAT_PROMPT_LENGTH) {
    throw new Error('A pergunta com o identificador excede 8.000 caracteres. Reduza o texto antes de enviar.');
  }
  return outgoingPrompt;
}
