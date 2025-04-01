import { useEffect, useState } from "react";
import axios from "axios";

const Quiz = ({ category }) => {
    const [questions, setQuestions] = useState([]);
    const [userAnswers, setUserAnswers] = useState({});
    const [score, setScore] = useState(null);

    useEffect(() => {
        axios.get(`http://localhost:5000/quiz/${category}`)
            .then(response => setQuestions(response.data))
            .catch(error => console.error("Error fetching quiz:", error));
    }, [category]);

    const handleAnswerChange = (questionId, selectedAnswer) => {
        setUserAnswers({ ...userAnswers, [questionId]: selectedAnswer });
    };

    const handleSubmit = async () => {
        const answers = Object.keys(userAnswers).map(questionId => ({
            questionId,
            selectedAnswer: userAnswers[questionId]
        }));

        const response = await axios.post("http://localhost:5000/quiz/submit", { answers });
        setScore(response.data.score);
    };

    return (
        <div>
            <h2>Quiz on {category}</h2>

            {questions.map((q) => (
                <div key={q._id}>
                    <h4>{q.question}</h4>
                    {q.options.map((option, index) => (
                        <label key={index}>
                            <input
                                type="radio"
                                name={q._id}
                                value={option}
                                onChange={() => handleAnswerChange(q._id, option)}
                            />
                            {option}
                        </label>
                    ))}
                </div>
            ))}

            <button onClick={handleSubmit}>Submit Quiz</button>

            {score !== null && <h3>Your Score: {score} / {questions.length}</h3>}
        </div>
    );
};

export default Quiz;
