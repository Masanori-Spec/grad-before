import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests/browser',timeout:45000,workers:1,retries:0,reporter:[['list'],['html',{open:'never'}]],use:{viewport:{width:560,height:200},launchOptions:{chromiumSandbox:true}}});
