import styles from "./RelatedQuestions.module.css";

export function RelatedQuestions({
  questions,
  onSelect,
  disabled,
}: {
  questions: string[];
  onSelect: (q: string) => void;
  disabled?: boolean;
}) {
  if (questions.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <p className={styles.label}>Follow-up questions</p>
      <div className={styles.list}>
        {questions.map((q, i) => (
          <button
            key={i}
            type="button"
            className={styles.button}
            disabled={disabled}
            onClick={() => onSelect(q)}
          >
            <span>{q}</span>
            <span className={styles.arrow}>→</span>
          </button>
        ))}
      </div>
    </div>
  );
}
