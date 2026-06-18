// dashboard/static/dashboard/js/dashboard.js

let charts = {};

// 1. الدالة الرئيسية للتشغيل
function initDashboard() {
    console.log("🚀 جاري تشغيل لوحة التحكم التعليمية...");
    setupFilter();
    loadDataFromServer(); // جلب البيانات فوراً عند التحميل
}

// 2. جلب البيانات من السيرفر
async function loadDataFromServer() {
    try {
        const response = await fetch('/dashboard/overview/');
        const data = await response.json();

        // ✅ تحقق قبل استخدام class_avg_scores
        if (data.academic && Array.isArray(data.academic.class_avg_scores)) {
            const length = data.academic.class_avg_scores.length;
            updateMetrics(length);
        } else {
            console.warn("class_avg_scores غير موجودة أو فارغة");
            updateMetrics(0); // قيمة افتراضية
        }

        // باقي التحديثات في الـ Dashboard
        renderCharts(data);
        renderAttendance(data.engagement.attendance_stats);
        renderAssignments(data.engagement.assignments);

    } catch (error) {
        console.error("فشل جلب البيانات:", error);
    }
}

// 3. تحديث بطاقات المؤشرات
function updateMetrics(academicData) {
    const container = document.getElementById('metrics-cards');
    if (!container || !academicData) return;

    const avgScore = academicData.average_scores_by_subject.length
        ? Math.round(
            academicData.average_scores_by_subject.reduce((acc, s) => acc + s.avg_score, 0)
            / academicData.average_scores_by_subject.length
          )
        : 0;

    const pass = academicData.pass_fail_ratio?.passed || 0;
    const fail = academicData.pass_fail_ratio?.failed || 0;
    const passRate = pass + fail > 0 ? Math.round((pass / (pass + fail)) * 100) : 0;

    // مثال بسيط للواجبات (يمكن تعديل لاحقاً)
    const assignmentRate = 75; // placeholder
    const needsAttention = 5;  // placeholder

    const cards = [
        { label: 'متوسط الدرجات', value: avgScore + '%', color: 'bg-primary' },
        { label: 'نسبة النجاح', value: passRate + '%', color: 'bg-success' },
        { label: 'إنجاز الواجبات', value: assignmentRate + '%', color: 'bg-info' },
        { label: 'الطلاب المحتاجون اهتمام', value: needsAttention, color: 'bg-danger' }
    ];

    container.innerHTML = cards.map(card => `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card text-white ${card.color}">
                <div class="card-body">
                    <h6 class="card-title">${card.label}</h6>
                    <h2 class="mb-0">${card.value}</h2>
                </div>
            </div>
        </div>
    `).join('');
}

// 4. تحديث الرسوم البيانية
function updateCharts(academicData, engagementData) {
    // الأداء عبر الزمن (Line Chart)
    const performanceData = academicData.progress_over_time || [];
    const ctxLine = document.getElementById('performanceChart');
    if (ctxLine) {
        if (charts.performance) charts.performance.destroy();
        charts.performance = new Chart(ctxLine, {
            type: 'line',
            data: {
                labels: performanceData.map(d => new Date(d.month).toLocaleDateString()),
                datasets: [{
                    label: 'متوسط الدرجات',
                    data: performanceData.map(d => d.avg_score),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75,192,192,0.2)',
                    tension: 0.1
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // الحضور (Bar Chart)
    const attendanceData = engagementData.attendance_stats || [];
    const ctxBar = document.getElementById('attendanceChart');
    if (ctxBar) {
        if (charts.attendance) charts.attendance.destroy();
        charts.attendance = new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: attendanceData.map(a => a.status),
                datasets: [{
                    label: 'عدد الطلاب',
                    data: attendanceData.map(a => a.count),
                    backgroundColor: 'rgba(54, 162, 235, 0.7)'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // الواجبات (Bar Chart) - هنا يمكن ربطها بالـ API لاحقاً
    const ctxAssignment = document.getElementById('assignmentChart');
    if (ctxAssignment) {
        if (charts.assignment) charts.assignment.destroy();
        charts.assignment = new Chart(ctxAssignment, {
            type: 'bar',
            data: {
                labels: ['واجب 1', 'واجب 2', 'واجب 3'], // placeholder
                datasets: [{
                    label: 'نسبة الإنجاز %',
                    data: [70, 85, 60], // placeholder
                    backgroundColor: 'rgba(255, 159, 64, 0.7)'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

// 5. إعداد الفلاتر
function setupFilter() {
    ['class-select', 'subject-select'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', loadDataFromServer);
    });
}

// تشغيل عند التحميل
document.addEventListener('DOMContentLoaded', initDashboard);
