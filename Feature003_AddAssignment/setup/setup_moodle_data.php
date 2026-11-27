<?php
// Creates the preconditions of Feature 3 (Add Assignment) on the mutms/demo Moodle site:
//   - course "Software Testing F3" (shortname F3TEST) with 3 topic sections
//   - user teacher / teacher  (enrolled as editing teacher)
//   - user student / student  (enrolled as student)
// Safe to run several times (existing course/users are reused).
//
// Run from the mutms/demo folder (the script is read from stdin, nothing is copied into the site):
//   docker compose exec -T -u www-data webserver php < ../Project3_AddAssignment/setup/setup_moodle_data.php
// It prints the course id; put it in COURSE_ID of Level1/data/variables.csv and Level2/config/site.csv.

define('CLI_SCRIPT', true);
require('/var/www/site/moodle/config.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/enrollib.php');

$course = $DB->get_record('course', ['shortname' => 'F3TEST']);
if (!$course) {
    $course = create_course((object)[
        'fullname' => 'Software Testing F3', 'shortname' => 'F3TEST', 'category' => 1,
        'format' => 'topics', 'numsections' => 3, 'summary' => 'Course used by the Feature 3 tests',
    ]);
}

function f3_user($username, $first, $last) {
    global $DB, $CFG;
    $user = $DB->get_record('user', ['username' => $username, 'deleted' => 0, 'mnethostid' => $CFG->mnet_localhost_id]);
    if (!$user) {
        $id = user_create_user((object)[
            'username' => $username, 'password' => $username, 'firstname' => $first, 'lastname' => $last,
            'email' => $username . '@example.com', 'auth' => 'manual', 'confirmed' => 1,
            'mnethostid' => $CFG->mnet_localhost_id, 'lang' => 'en',
        ], true, false);
        $user = $DB->get_record('user', ['id' => $id]);
    }
    return $user;
}

$teacher = f3_user('teacher', 'Test', 'Teacher');
$student = f3_user('student', 'Test', 'Student');

$plugin = enrol_get_plugin('manual');
$instance = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual']);
if (!$instance) {
    $plugin->add_instance($course, ['status' => ENROL_INSTANCE_ENABLED, 'enrolperiod' => 0, 'expirynotify' => 0,
        'expirythreshold' => 86400, 'roleid' => $DB->get_field('role', 'id', ['shortname' => 'student'])]);
    $instance = $DB->get_record('enrol', ['courseid' => $course->id, 'enrol' => 'manual'], '*', MUST_EXIST);
}
$roles = ['editingteacher' => $teacher, 'student' => $student];
foreach ($roles as $shortname => $user) {
    $roleid = $DB->get_field('role', 'id', ['shortname' => $shortname], MUST_EXIST);
    $plugin->enrol_user($instance, $user->id, $roleid);
}

echo "COURSE_ID={$course->id}\n";
echo "teacher id={$teacher->id}, student id={$student->id}\n";
