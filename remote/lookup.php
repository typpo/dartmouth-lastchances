<?php
//
// Calls DND lookup program for multiple comma-separated names
//
$names = explode(',', $_GET['names']);
$ret = array();
foreach ($names as $name) {
    if ($name == "") {
        continue;
    }
    $cmd = escapeshellcmd($name);
    if ($cmd !== "") {
        $results = array();
        exec("dndlookup -f name \"$cmd\"", $results);           // if dndlookup is installed
        //exec("python dnd.py \"$cmd\"", $results);             // if it isn't
        $ret[] = implode("\n", $results);
    }
}
echo implode('#', $ret);
?>
