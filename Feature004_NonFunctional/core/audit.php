// Executed via `docker exec -i <container> php -r ...` with JSON payload on stdin.
define('CLI_SCRIPT', true);
$input = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$paths = empty($input['config']) ? [
    '/var/www/site/moodle/config.php',
    getcwd() . '/config.php',
    '/var/www/html/config.php',
    '/var/www/moodle/config.php',
] : [$input['config']];

$path = null;
foreach ($paths as $p) {
    if (is_file($p)) {
        $path = $p;
        break;
    }
}
if (!$path) {
    throw new RuntimeException('Moodle config.php not found; set MOODLE_CONFIG_PATH');
}
require $path;

if (rtrim($CFG->wwwroot, '/') !== rtrim($input['base'], '/')) {
    throw new RuntimeException('Moodle wwwroot differs from configured target');
}

$op = $input['op'];
$courseid = (int)($input['course_id'] ?? 2);
$out = ['ok' => true, 'release' => $CFG->release ?? ''];

if ($op === 'capability') {
    $u = $DB->get_record(
        'user',
        ['username' => $input['username'], 'mnethostid' => $CFG->mnet_localhost_id, 'deleted' => 0],
        '*',
        MUST_EXIST
    );
    $course = $DB->get_record('course', ['id' => $courseid], 'id,fullname,shortname', MUST_EXIST);
    $ctx = context_course::instance($course->id);
    $out['is_admin'] = is_siteadmin($u);
    $out['suspended'] = (bool)$u->suspended;
    $out['can_add_quiz'] = has_capability('moodle/course:manageactivities', $ctx, $u->id)
        && has_capability('mod/quiz:addinstance', $ctx, $u->id);
    $out['course'] = ['id' => (int)$course->id, 'shortname' => $course->shortname, 'fullname' => $course->fullname];
} else {
    $prefix = $input['prefix'] ?? '';
    if (!preg_match('/^nfr4[a-f0-9]{12}_$/D', $prefix)) {
        throw new RuntimeException('Invalid NFR4 run prefix');
    }
    $names = array_values(array_unique($input['names'] ?? []));
    foreach ($names as $n) {
        if (!preg_match('/^' . preg_quote($prefix, '/') . '[a-f0-9]{16}$/D', $n)) {
            throw new RuntimeException('Quiz name outside NFR4 run namespace: ' . $n);
        }
    }

    $quizmod = $DB->get_record('modules', ['name' => 'quiz'], 'id', MUST_EXIST);
    $out['quizzes'] = [];
    foreach (array_chunk($names, 200) as $chunk) {
        if (empty($chunk)) {
            continue;
        }
        list($insql, $params) = $DB->get_in_or_equal($chunk, SQL_PARAMS_QM);
        array_unshift($params, $courseid, (int)$quizmod->id);
        $sql = "SELECT cm.id AS cmid, q.id AS quizid, q.name, cm.section
                  FROM {course_modules} cm
                  JOIN {quiz} q ON q.id = cm.instance
                 WHERE cm.course = ? AND cm.module = ? AND cm.deletioninprogress = 0 AND q.name $insql
                 ORDER BY cm.id ASC";
        foreach ($DB->get_records_sql($sql, $params) as $rec) {
            $out['quizzes'][$rec->name][] = [
                'cmid' => (int)$rec->cmid,
                'quizid' => (int)$rec->quizid,
                'section' => (int)$rec->section,
            ];
        }
    }

    if ($op === 'cleanup') {
        require_once($CFG->dirroot . '/course/lib.php');
        $out['deleted'] = [];
        foreach ($out['quizzes'] as $qname => $entries) {
            if (strpos($qname, $prefix) !== 0) {
                throw new RuntimeException('Refusing cleanup of non-NFR4 quiz');
            }
            foreach ($entries as $entry) {
                course_delete_module($entry['cmid']);
                $out['deleted'][] = ['name' => $qname, 'cmid' => $entry['cmid']];
            }
        }
    } elseif ($op !== 'audit') {
        throw new RuntimeException('Unknown operation: ' . $op);
    }
}

echo "\nNFR4_JSON:" . json_encode($out, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE) . "\n";
