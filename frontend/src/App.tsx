import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { ConfirmProvider } from "./context/ConfirmContext";
import ProtectedRoute from "./components/layout/ProtectedRoute";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Resume from "./pages/Resume";
import InterviewRoom from "./pages/InterviewRoom";
import CodingList from "./pages/CodingList";
import CodingProblem from "./pages/CodingProblem";
import Performance from "./pages/Performance";
import PreparationPlan from "./pages/PreparationPlan";
import InterviewHistory from "./pages/InterviewHistory";
import InterviewDetail from "./pages/InterviewDetail";
import Profile from "./pages/Profile";
import SkillGap from "./pages/SkillGap";
import Roadmap from "./pages/Roadmap";
import Analytics from "./pages/Analytics";
import Companies from "./pages/Companies";
import Assistant from "./pages/Assistant";
import NotFound from "./pages/NotFound";

const P = ({ children }: { children: React.ReactNode }) => <ProtectedRoute>{children}</ProtectedRoute>;

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <ConfirmProvider>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<P><Dashboard /></P>} />
                <Route path="/resume" element={<P><Resume /></P>} />
                <Route path="/interview/:type" element={<P><InterviewRoom /></P>} />
                <Route path="/coding" element={<P><CodingList /></P>} />
                <Route path="/coding/:id" element={<P><CodingProblem /></P>} />
                <Route path="/performance" element={<P><Performance /></P>} />
                <Route path="/analytics" element={<P><Analytics /></P>} />
                <Route path="/preparation-plan" element={<P><PreparationPlan /></P>} />
                <Route path="/skill-gap" element={<P><SkillGap /></P>} />
                <Route path="/roadmap" element={<P><Roadmap /></P>} />
                <Route path="/companies" element={<P><Companies /></P>} />
                <Route path="/assistant" element={<P><Assistant /></P>} />
                <Route path="/history" element={<P><InterviewHistory /></P>} />
                <Route path="/history/:id" element={<P><InterviewDetail /></P>} />
                <Route path="/profile" element={<P><Profile /></P>} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </ConfirmProvider>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
