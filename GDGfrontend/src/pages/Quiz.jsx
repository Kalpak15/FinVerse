import React, { useState } from 'react';
import { ArrowRight, ArrowLeft } from 'lucide-react';

const FinVerseQuiz = () => {
  // Sample quiz questions
  const questions = [
    {
      id: 1,
      question: "Which investment strategy focuses on companies with potential for above-average growth?",
      options: [
        "Value investing", 
        "Growth investing", 
        "Income investing", 
        "Index investing"
      ],
      correctAnswer: 1
    },
    {
      id: 2,
      question: "What is the term for the loss in purchasing power of money due to rising prices?",
      options: [
        "Deflation", 
        "Depreciation", 
        "Inflation", 
        "Stagnation"
      ],
      correctAnswer: 2
    },
    {
      id: 3,
      question: "Which financial ratio measures a company's ability to pay short-term obligations?",
      options: [
        "Price-to-Earnings Ratio", 
        "Debt-to-Equity Ratio", 
        "Current Ratio", 
        "Return on Equity"
      ],
      correctAnswer: 2
    }
  ];

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [quizCompleted, setQuizCompleted] = useState(false);
  const [score, setScore] = useState(0);

  const handleOptionSelect = (index) => {
    setSelectedOption(index);
  };

  const handleNext = () => {
    // Update score if correct
    if (selectedOption === questions[currentQuestion].correctAnswer) {
      setScore(score + 1);
    }
    
    // Move to next question or finish quiz
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedOption(null);
    } else {
      setQuizCompleted(true);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
      setSelectedOption(null);
    }
  };

  const resetQuiz = () => {
    setCurrentQuestion(0);
    setSelectedOption(null);
    setQuizCompleted(false);
    setScore(0);
  };

  const progressPercentage = ((currentQuestion + 1) / questions.length) * 100;

  return (
    <div className="min-h-screen bg-[#0c1126] text-white flex flex-col" style={{
      backgroundImage: "radial-gradient(circle, rgba(52, 86, 168, 0.1) 1px, transparent 1px)",
      backgroundSize: "30px 30px"
    }}>
      {/* Header */}
      <header className="flex justify-between items-center p-4 md:px-8 bg-[rgba(13,19,42,0.7)] backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="bg-[#4285f4] text-white px-3 py-1 rounded-full font-bold">FinVerse</div>
          <span className="font-bold hidden md:inline">FinVerse</span>
        </div>
        
        <nav className="hidden md:flex gap-6">
          <a href="#" className="hover:text-[#4285f4] transition-colors">Home</a>
          <a href="#" className="hover:text-[#4285f4] transition-colors">About</a>
          <a href="#" className="hover:text-[#4285f4] transition-colors">Contact</a>
          <a href="#" className="hover:text-[#4285f4] transition-colors">Testimonials</a>
        </nav>
        
        <button className="bg-[#4285f4] text-white px-4 py-2 rounded-lg hover:bg-[#3367d6] transition-colors">
          Logout
        </button>
      </header>

      {/* Main Content */}
      <div className="max-w-3xl mx-auto w-full px-4 py-8 flex-1 flex flex-col">
        {!quizCompleted ? (
          <>
            {/* Quiz Header & Progress */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-[#4285f4] to-[#a855f7] bg-clip-text text-transparent">
                Financial Literacy Quiz
              </h1>
              <p className="text-gray-400">Test your financial knowledge and improve your skills</p>
              
              <div className="flex items-center justify-between mt-6">
                <span className="text-sm text-gray-400">Question {currentQuestion + 1}/{questions.length}</span>
                <div className="flex-1 mx-4 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-[#4285f4] to-[#a855f7] rounded-full"
                    style={{ width: `${progressPercentage}%` }}
                  ></div>
                </div>
                <span className="text-sm text-gray-400">{Math.round(progressPercentage)}%</span>
              </div>
            </div>
            
            {/* Question Card */}
            <div className="bg-[rgba(20,30,60,0.5)] backdrop-blur-sm p-6 rounded-xl border border-[rgba(255,255,255,0.1)] shadow-lg mb-6">
              <h2 className="text-xl font-medium mb-6">{questions[currentQuestion].question}</h2>
              
              <div className="space-y-3">
                {questions[currentQuestion].options.map((option, index) => (
                  <div 
                    key={index}
                    className={`p-4 rounded-lg cursor-pointer transition-all ${
                      selectedOption === index 
                        ? 'bg-[#4285f4] text-white' 
                        : 'bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)]'
                    }`}
                    onClick={() => handleOptionSelect(index)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center border ${
                        selectedOption === index 
                          ? 'border-white bg-white text-[#4285f4]' 
                          : 'border-gray-400'
                      }`}>
                        {String.fromCharCode(65 + index)}
                      </div>
                      <span>{option}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Navigation Buttons */}
            <div className="flex justify-between mt-auto">
              <button 
                onClick={handlePrevious}
                disabled={currentQuestion === 0}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  currentQuestion === 0 
                    ? 'text-gray-500 cursor-not-allowed' 
                    : 'text-white hover:bg-[rgba(255,255,255,0.1)]'
                }`}
              >
                <ArrowLeft size={16} />
                Previous
              </button>
              
              <button 
                onClick={handleNext}
                disabled={selectedOption === null}
                className={`flex items-center gap-2 px-6 py-2 rounded-lg ${
                  selectedOption === null 
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                    : 'bg-[#4285f4] text-white hover:bg-[#3367d6]'
                }`}
              >
                {currentQuestion === questions.length - 1 ? 'Finish' : 'Next'}
                <ArrowRight size={16} />
              </button>
            </div>
          </>
        ) : (
          /* Quiz Results */
          <div className="bg-[rgba(20,30,60,0.5)] backdrop-blur-sm p-8 rounded-xl border border-[rgba(255,255,255,0.1)] shadow-lg text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-[#4285f4] to-[#a855f7] rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-2xl font-bold">{score}/{questions.length}</span>
            </div>
            
            <h2 className="text-2xl font-bold mb-2">Quiz Completed!</h2>
            <p className="text-gray-400 mb-6">
              {score === questions.length 
                ? "Perfect score! You're a financial expert!" 
                : score >= questions.length / 2 
                  ? "Good job! You have a solid understanding of financial concepts." 
                  : "Keep learning! Review the concepts to improve your financial literacy."}
            </p>
            
            <button 
              onClick={resetQuiz}
              className="bg-[#4285f4] text-white px-6 py-3 rounded-lg hover:bg-[#3367d6] transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default FinVerseQuiz;