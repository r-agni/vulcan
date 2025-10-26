import { useState, useEffect } from 'react';
import styles from './StaffDashboard.module.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function StaffDashboard() {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [assignments, setAssignments] = useState([]);

  useEffect(() => {
    fetchStaffList();
  }, []);

  const fetchStaffList = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/staff/list`);
      if (response.ok) {
        const data = await response.json();
        setStaff(data);
      }
    } catch (error) {
      console.error('Error fetching staff:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssignments = async (staffId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/staff/assignments/${staffId}`);
      if (response.ok) {
        const data = await response.json();
        setAssignments(data);
      }
    } catch (error) {
      console.error('Error fetching assignments:', error);
    }
  };

  const handleClockIn = async (employeeId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/staff/clock-in?employee_id=${employeeId}`, {
        method: 'POST',
      });

      if (response.ok) {
        await fetchStaffList();
        alert('Clocked in successfully!');
      }
    } catch (error) {
      alert('Error clocking in: ' + error.message);
    }
  };

  const handleClockOut = async (employeeId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/staff/clock-out?employee_id=${employeeId}`, {
        method: 'POST',
      });

      if (response.ok) {
        await fetchStaffList();
        alert('Clocked out successfully!');
      }
    } catch (error) {
      alert('Error clocking out: ' + error.message);
    }
  };

  const handleCompleteAssignment = async (alertId, outcome) => {
    try {
      const notes = prompt('Enter completion notes (optional):');
      const response = await fetch(
        `${API_BASE_URL}/api/staff/assignment/${alertId}/complete?outcome=${outcome}&notes=${encodeURIComponent(notes || '')}`,
        { method: 'POST' }
      );

      if (response.ok) {
        if (selectedStaff) {
          await fetchAssignments(selectedStaff.id);
        }
        alert('Assignment completed!');
      }
    } catch (error) {
      alert('Error completing assignment: ' + error.message);
    }
  };

  const handleStaffClick = (staffMember) => {
    setSelectedStaff(staffMember);
    fetchAssignments(staffMember.id);
  };

  if (loading) {
    return <div className={styles.loading}>Loading staff...</div>;
  }

  return (
    <div className={styles.staffDashboard}>
      <div className={styles.header}>
        <h2 className={styles.title}>Staff Management</h2>
        <div className={styles.stats}>
          <div className={styles.statCard}>
            <span className={styles.statValue}>{staff.filter(s => s.is_on_duty).length}</span>
            <span className={styles.statLabel}>On Duty</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statValue}>{staff.length}</span>
            <span className={styles.statLabel}>Total Staff</span>
          </div>
        </div>
      </div>

      <div className={styles.content}>
        {/* Staff List */}
        <div className={styles.staffList}>
          <h3 className={styles.sectionTitle}>Staff Members</h3>
          {staff.length === 0 ? (
            <div className={styles.emptyState}>No staff members found</div>
          ) : (
            staff.map((member) => (
              <div
                key={member.id}
                className={`${styles.staffCard} ${selectedStaff?.id === member.id ? styles.selected : ''}`}
                onClick={() => handleStaffClick(member)}
              >
                <div className={styles.staffInfo}>
                  <div className={styles.staffName}>
                    <span className={`${styles.statusDot} ${member.is_on_duty ? styles.onDuty : styles.offDuty}`} />
                    {member.name}
                  </div>
                  <div className={styles.staffRole}>{member.role}</div>
                  <div className={styles.staffId}>ID: {member.employee_id}</div>
                </div>

                <div className={styles.staffActions}>
                  {member.is_on_duty ? (
                    <>
                      <div className={styles.shiftInfo}>
                        Started: {member.shift_start ? new Date(member.shift_start).toLocaleTimeString() : 'N/A'}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleClockOut(member.employee_id);
                        }}
                        className={styles.clockOutButton}
                      >
                        Clock Out
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClockIn(member.employee_id);
                      }}
                      className={styles.clockInButton}
                    >
                      Clock In
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Assignments Panel */}
        {selectedStaff && (
          <div className={styles.assignmentsPanel}>
            <h3 className={styles.sectionTitle}>
              Active Assignments - {selectedStaff.name}
            </h3>
            {assignments.length === 0 ? (
              <div className={styles.emptyState}>No active assignments</div>
            ) : (
              <div className={styles.assignmentsList}>
                {assignments.map((assignment) => (
                  <div key={assignment.alert_id} className={styles.assignmentCard}>
                    <div className={styles.assignmentHeader}>
                      <span className={styles.alertId}>Alert #{assignment.alert_id.slice(0, 8)}</span>
                      <span className={styles.elapsed}>
                        {Math.floor(assignment.time_elapsed / 60)}m {assignment.time_elapsed % 60}s ago
                      </span>
                    </div>
                    <div className={styles.assignmentTime}>
                      Assigned: {new Date(assignment.assigned_at).toLocaleString()}
                    </div>
                    <div className={styles.assignmentActions}>
                      <button
                        onClick={() => handleCompleteAssignment(assignment.alert_id, 'success')}
                        className={styles.completeButton}
                      >
                        Complete
                      </button>
                      <button
                        onClick={() => handleCompleteAssignment(assignment.alert_id, 'failed')}
                        className={styles.failButton}
                      >
                        Failed
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default StaffDashboard;
