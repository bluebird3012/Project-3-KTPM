// Executed via php -r in the local Moodle container. JSON input via stdin.
define('CLI_SCRIPT', true);
$input = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$paths = empty($input['config']) ? [getcwd().'/config.php', '/var/www/html/config.php', '/var/www/html/public/config.php', '/var/www/moodle/config.php', '/var/www/moodle/public/config.php', '/var/www/html/moodle/config.php', '/var/www/html/moodle/public/config.php', '/opt/moodle/config.php'] : [$input['config']];
$path = null;
foreach ($paths as $p) { if (is_file($p)) { $path = $p; break; } }
if (!$path) { throw new RuntimeException('Moodle config.php not found; set MOODLE_CONFIG_PATH'); }
require $path;
if (rtrim($CFG->wwwroot, '/') !== rtrim($input['base'], '/')) { throw new RuntimeException('Moodle wwwroot differs from configured target'); }
$op = $input['op'];
$out = ['ok' => true];
if ($op === 'capability') {
    $u = $DB->get_record('user', ['username'=>$input['username'], 'mnethostid'=>$CFG->mnet_localhost_id, 'deleted'=>0], '*', MUST_EXIST);
    $out['can_create'] = has_capability('moodle/user:create', context_system::instance(), $u->id);
    $out['is_admin'] = is_siteadmin($u);
    $out['suspended'] = (bool)$u->suspended;
    $out['roles'] = array_values($DB->get_fieldset_sql('SELECT DISTINCT r.shortname FROM {role} r JOIN {role_assignments} ra ON ra.roleid = r.id WHERE ra.userid = ?', [$u->id]));
} else {
    $prefix = $input['prefix'];
    if (!preg_match('/^nfr[a-f0-9]{12}_$/D', $prefix)) { throw new RuntimeException('Invalid run prefix'); }
    $names = array_values(array_unique($input['names']));
    foreach ($names as $n) {
        if (!preg_match('/^'.preg_quote($prefix, '/').'[a-f0-9]{16}$/D', $n)) { throw new RuntimeException('Username outside run namespace'); }
    }
    $out['users'] = [];
    foreach (array_chunk($names, 200) as $chunk) {
        foreach ($DB->get_records_list('user', 'username', $chunk, '', 'id,username,email,deleted,mnethostid') as $record) {
            if ($record->deleted || $record->mnethostid != $CFG->mnet_localhost_id) { continue; }
            $out['users'][$record->username][] = ['id'=>(int)$record->id, 'email'=>$record->email];
        }
    }
    if ($op === 'cleanup') {
        require_once($CFG->dirroot.'/user/lib.php');
        $out['deleted'] = [];
        foreach ($out['users'] as $name => $records) {
            foreach ($records as $record) {
                $u = $DB->get_record('user', ['id'=>$record['id']], '*', MUST_EXIST);
                if (is_siteadmin($u) || isguestuser($u) || $u->username !== $name || $u->email !== $name.'@example.invalid') { throw new RuntimeException('Refusing cleanup of non-test account'); }
                if (!delete_user($u)) { throw new RuntimeException('Moodle delete_user failed'); }
                $out['deleted'][] = $name;
            }
        }
    } elseif ($op !== 'audit') { throw new RuntimeException('Unknown operation'); }
}
echo "\nNFR_JSON:".json_encode($out, JSON_THROW_ON_ERROR)."\n";
