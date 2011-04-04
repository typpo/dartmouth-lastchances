<?php
//
// Calls DND lookup program for multiple names
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
        exec("dndlookup -f name \"$cmd\"", $results);
        $ret[] = implode("\n", $results);
    }
}
echo implode('#', $ret);
?>
