<?php
$names = explode(',', $_GET['names']);
$year= $_GET['year'];
$ret = array();
foreach ($names as $name) {
    if ($name == "") {
        continue;
    }   
    $name = escapeshellcmd(stripcslashes($name));
    $year = escapeshellcmd(stripcslashes($year));
    if ($name !== "") {
        $results = array();
        // exec("dndlookup -f name \"$name\" -f deptclass \"$year\"", $results);            // if dndlookup is installed
        exec("python dnd.py \"$name\" \"$year\"", $results);                                // if it isn't
        $ret[] = implode("\n", $results);
    }   
}
echo implode('#', $ret);
?>
