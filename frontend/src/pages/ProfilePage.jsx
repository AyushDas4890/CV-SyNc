import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";
import "../styles.css";

export default function ProfilePage() {
  const [username, setUsername] = useState("");
  const [profile, setProfile] = useState({
    fullName: "",
    phone: "",
    email: "",
    githubUrl: "",
    linkedinUrl: "",
  });

  const [educationList, setEducationList] = useState([
    { institution: "", degree: "", fieldOfStudy: "", dates: "", gpa: "" },
  ]);

  const [achievementsList, setAchievementsList] = useState([
    { title: "", description: "", date: "" },
  ]);

  const [certificatesList, setCertificatesList] = useState([
    { name: "", issuer: "", date: "", link: "" },
  ]);

  const navigate = useNavigate();

  useEffect(() => {
    api.me()
      .then((res) => {
        setUsername(res.githubUsername || res.displayName || "");
        setProfile((prev) => ({
          ...prev,
          email: res.email || prev.email,
          fullName: res.displayName || prev.fullName,
          githubUrl: res.githubUsername ? `https://github.com/${res.githubUsername}` : prev.githubUrl,
        }));
      })
      .catch(() => navigate("/auth"));

    // Load any previously saved profile from the server
    api.getProfile()
      .then((res) => {
        if (res.studentProfile) {
          const { profile: savedProfile, education: savedEducation, achievements: savedAchievements, certificates: savedCertificates } = res.studentProfile;
          if (savedProfile) {
            setProfile((prev) => ({ ...prev, ...savedProfile }));
          }
          if (savedEducation && savedEducation.length > 0) {
            setEducationList(savedEducation);
          }
          if (savedAchievements && savedAchievements.length > 0) {
            setAchievementsList(savedAchievements);
          }
          if (savedCertificates && savedCertificates.length > 0) {
            setCertificatesList(savedCertificates);
          }
        }
      })
      .catch(() => {}); // non-fatal: user might not have a profile yet
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleProfileChange(e) {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  }

  function handleEducationChange(index, field, value) {
    const updated = [...educationList];
    updated[index][field] = value;
    setEducationList(updated);
  }

  function addEducation() {
    setEducationList([
      ...educationList,
      { institution: "", degree: "", fieldOfStudy: "", dates: "", gpa: "" },
    ]);
  }

  function removeEducation(index) {
    if (educationList.length === 1) return;
    setEducationList(educationList.filter((_, i) => i !== index));
  }

  function handleAchievementChange(index, field, value) {
    const updated = [...achievementsList];
    updated[index][field] = value;
    setAchievementsList(updated);
  }

  function addAchievement() {
    setAchievementsList([
      ...achievementsList,
      { title: "", description: "", date: "" },
    ]);
  }

  function removeAchievement(index) {
    if (achievementsList.length === 1) return;
    setAchievementsList(achievementsList.filter((_, i) => i !== index));
  }

  function handleCertificateChange(index, field, value) {
    const updated = [...certificatesList];
    updated[index][field] = value;
    setCertificatesList(updated);
  }

  function addCertificate() {
    setCertificatesList([
      ...certificatesList,
      { name: "", issuer: "", date: "", link: "" },
    ]);
  }

  function removeCertificate(index) {
    if (certificatesList.length === 1) return;
    setCertificatesList(certificatesList.filter((_, i) => i !== index));
  }

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  async function proceed() {
    const studentData = {
      profile,
      education: educationList.filter((edu) => edu.institution || edu.degree),
      achievements: achievementsList.filter((ach) => ach.title || ach.description),
      certificates: certificatesList.filter((cert) => cert.name || cert.issuer),
    };

    // Mirror to localStorage immediately so subsequent pages can read it
    localStorage.setItem("cv_sync_student_profile", JSON.stringify(studentData));

    // Persist to backend
    setIsSaving(true);
    setSaveError("");
    try {
      await api.saveProfile(studentData);
    } catch (err) {
      // Non-blocking: warn but don't stop the user navigating forward
      setSaveError("Could not save to server — your data is cached locally.");
    } finally {
      setIsSaving(false);
    }

    navigate("/onboarding/experience");
  }

  return (
    <div className="page-root">
      <LogoutBar username={username} />

      <div className="page-content">
        {/* Step indicator (5 steps) */}
        <div className="step-indicator">
          <div className="step-item done">
            <div className="step-dot">✓</div>
            <span>Account</span>
          </div>
          <div className="step-connector" />
          <div className="step-item active">
            <div className="step-dot">2</div>
            <span>Profile</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">3</div>
            <span>Experience</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">4</div>
            <span>GitHub</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">5</div>
            <span>Template</span>
          </div>
        </div>

        {/* Heading */}
        <div className="page-heading">
          <h1>Student Profile & Background</h1>
          <p className="sub">Provide your contact details, education, achievements, and certifications.</p>
        </div>

        {/* Profile Card */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", color: "var(--gold)", marginBottom: "16px" }}>Personal Details</h2>
          <div className="row-2col">
            <div className="field">
              <label>Full Name</label>
              <input
                name="fullName"
                placeholder="e.g. Alex Chen"
                value={profile.fullName}
                onChange={handleProfileChange}
              />
            </div>
            <div className="field">
              <label>Phone Number</label>
              <input
                name="phone"
                placeholder="+1 (555) 019-2834"
                value={profile.phone}
                onChange={handleProfileChange}
              />
            </div>
          </div>

          <div className="field">
            <label>Email Address</label>
            <input
              name="email"
              type="email"
              placeholder="alex.chen@university.edu"
              value={profile.email}
              onChange={handleProfileChange}
            />
          </div>

          <div className="row-2col">
            <div className="field">
              <label>GitHub Profile Link</label>
              <input
                name="githubUrl"
                placeholder="https://github.com/alexchen"
                value={profile.githubUrl}
                onChange={handleProfileChange}
              />
            </div>
            <div className="field">
              <label>LinkedIn Profile Link</label>
              <input
                name="linkedinUrl"
                placeholder="https://linkedin.com/in/alexchen"
                value={profile.linkedinUrl}
                onChange={handleProfileChange}
              />
            </div>
          </div>
        </div>

        {/* Education Card */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "1.1rem", color: "var(--gold)" }}>Education</h2>
            <button className="secondary" type="button" onClick={addEducation} style={{ padding: "6px 12px", fontSize: "0.85rem" }}>
              + Add Education
            </button>
          </div>

          {educationList.map((edu, idx) => (
            <div key={idx} style={{
              padding: "16px",
              background: "rgba(10, 22, 40, 0.4)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--navy-border)",
              marginBottom: idx < educationList.length - 1 ? "16px" : "0"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)" }}>
                  Education #{idx + 1}
                </span>
                {educationList.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeEducation(idx)}
                    style={{ background: "none", border: "none", color: "var(--error)", cursor: "pointer", fontSize: "0.85rem" }}
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="field">
                <label>Institution / University</label>
                <input
                  placeholder="e.g. Stanford University"
                  value={edu.institution}
                  onChange={(e) => handleEducationChange(idx, "institution", e.target.value)}
                />
              </div>

              <div className="row-2col">
                <div className="field">
                  <label>Degree</label>
                  <input
                    placeholder="e.g. B.S. in Computer Science"
                    value={edu.degree}
                    onChange={(e) => handleEducationChange(idx, "degree", e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Field of Study / Major</label>
                  <input
                    placeholder="e.g. Artificial Intelligence"
                    value={edu.fieldOfStudy}
                    onChange={(e) => handleEducationChange(idx, "fieldOfStudy", e.target.value)}
                  />
                </div>
              </div>

              <div className="row-2col">
                <div className="field">
                  <label>Dates / Graduation Year</label>
                  <input
                    placeholder="Sep 2021 – May 2025"
                    value={edu.dates}
                    onChange={(e) => handleEducationChange(idx, "dates", e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>CGPA / Percentage / GPA</label>
                  <input
                    placeholder="e.g. 8.7 / 10  or  87%  or  3.9 / 4.0"
                    value={edu.gpa}
                    onChange={(e) => handleEducationChange(idx, "gpa", e.target.value)}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Achievements Card */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "1.1rem", color: "var(--gold)" }}>Key Achievements & Honors</h2>
            <button className="secondary" type="button" onClick={addAchievement} style={{ padding: "6px 12px", fontSize: "0.85rem" }}>
              + Add Achievement
            </button>
          </div>

          {achievementsList.map((ach, idx) => (
            <div key={idx} style={{
              padding: "16px",
              background: "rgba(10, 22, 40, 0.4)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--navy-border)",
              marginBottom: idx < achievementsList.length - 1 ? "16px" : "0"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)" }}>
                  Achievement #{idx + 1}
                </span>
                {achievementsList.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeAchievement(idx)}
                    style={{ background: "none", border: "none", color: "var(--error)", cursor: "pointer", fontSize: "0.85rem" }}
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="row-2col">
                <div className="field">
                  <label>Achievement Title / Award</label>
                  <input
                    placeholder="e.g. 1st Place - Smart India Hackathon"
                    value={ach.title}
                    onChange={(e) => handleAchievementChange(idx, "title", e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Date / Year</label>
                  <input
                    placeholder="e.g. Nov 2024"
                    value={ach.date}
                    onChange={(e) => handleAchievementChange(idx, "date", e.target.value)}
                  />
                </div>
              </div>

              <div className="field">
                <label>Description / Details</label>
                <input
                  placeholder="e.g. Built an AI computer vision system out of 500+ competing university teams."
                  value={ach.description}
                  onChange={(e) => handleAchievementChange(idx, "description", e.target.value)}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Certifications Card */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "1.1rem", color: "var(--gold)" }}>Certifications & Credentials</h2>
            <button className="secondary" type="button" onClick={addCertificate} style={{ padding: "6px 12px", fontSize: "0.85rem" }}>
              + Add Certificate
            </button>
          </div>

          {certificatesList.map((cert, idx) => (
            <div key={idx} style={{
              padding: "16px",
              background: "rgba(10, 22, 40, 0.4)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--navy-border)",
              marginBottom: idx < certificatesList.length - 1 ? "16px" : "0"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)" }}>
                  Certificate #{idx + 1}
                </span>
                {certificatesList.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeCertificate(idx)}
                    style={{ background: "none", border: "none", color: "var(--error)", cursor: "pointer", fontSize: "0.85rem" }}
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="row-2col">
                <div className="field">
                  <label>Certificate Name</label>
                  <input
                    placeholder="e.g. AWS Certified Solutions Architect"
                    value={cert.name}
                    onChange={(e) => handleCertificateChange(idx, "name", e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Issuing Organization</label>
                  <input
                    placeholder="e.g. Amazon Web Services"
                    value={cert.issuer}
                    onChange={(e) => handleCertificateChange(idx, "issuer", e.target.value)}
                  />
                </div>
              </div>

              <div className="row-2col">
                <div className="field">
                  <label>Date Issued</label>
                  <input
                    placeholder="e.g. Jan 2025"
                    value={cert.date}
                    onChange={(e) => handleCertificateChange(idx, "date", e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Certificate URL / Verification Link</label>
                  <input
                    placeholder="https://credly.com/badges/your-credential-id"
                    value={cert.link}
                    onChange={(e) => handleCertificateChange(idx, "link", e.target.value)}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Navigation */}
        <div className="row" style={{ marginTop: "24px" }}>
          <button className="primary" onClick={proceed}>Continue to Experience</button>
          <button className="ghost" onClick={proceed}>Skip for now</button>
        </div>
      </div>
    </div>
  );

}
