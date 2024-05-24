#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label "windows"
  }
  
  triggers {
    pollSCM('H/2 * * * *')
  }

  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'10'))
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
    office365ConnectorWebhooks([[
                    name: "Office 365",
                    notifyBackToNormal: true,
                    startNotification: false,
                    notifyFailure: true,
                    notifySuccess: false,
                    notifyNotBuilt: false,
                    notifyAborted: false,
                    notifyRepeatedFailure: true,
                    notifyUnstable: true,
                    url: "${env.MSTEAMS_URL}"
            ]]
    )
  }

  stages {  
    stage("Checkout") {
      steps {
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
        setLatestGeniePath()
        echo "python3 path: ${env.PYTHON3_PATH}"
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch name: ${env.BRANCH_NAME}"
            echo "git branch: ${env.GIT_BRANCH}"
            echo "git local branch: ${env.GIT_LOCAL_BRANCH}"
            echo "git change id: ${env.CHANGE_ID}"
            echo "git change url: ${env.CHANGE_URL}"
        }
      }
    }
    
    stage("Run All Tests") {
      steps {
        bat """
            robocopy "\\\\isis.cclrc.ac.uk\\inst\$\\Kits\$\\CompGroup\\ICP\\EPICS_UTILS" "C:\\Instrument\\Apps\\EPICS_UTILS" /E /PURGE /R:2 /MT /XF "install.log" /NFL /NDL /NP
            set "PATH=%PATH%;C:\\Instrument\\Apps\\EPICS_UTILS"
                        
            set PYTHON3_PATH=${env.PYTHON3_PATH}
            %PYTHON3_PATH%\\Python\\python run_all_tests.py --output_dir ./test-reports
         """
      }
    }
        
    stage("Collate Unit Tests") {
      steps {
        junit '**/test-reports/TEST-*.xml'
        script {
          if (fileExists('**/cobertura.xml')) {
            cobertura coberturaReportFile: '**/cobertura.xml'
          }
        }
      }
    }

    stage("Record Coverage") {
        when { environment name: 'GIT_BRANCH', value: 'origin/master' }
        steps {            
            script {
                currentBuild.result = 'SUCCESS'
            }
            step([$class: 'MasterCoverageAction', scmVars: [GIT_URL: env.GIT_URL]])
        }
    }

    stage("PR Coverage to Github") {
        when { not { environment name: 'GIT_BRANCH', value: 'origin/master' }}
        steps {
            script {
                currentBuild.result = 'SUCCESS'
            }
            step([$class: 'CompareCoverageAction', scmVars: [GIT_URL: env.GIT_URL]])
        }
    }
    
  } 

  post {
    always {
        logParser ([
                projectRulePath: 'parse_rules',
                parsingRulesPath: '',
                showGraphs: true, 
                unstableOnWarning: false,
                useProjectRule: true,
        ])
    }
  } 
}

def setLatestGeniePath() {
        def basePath3 = '\\\\isis.cclrc.ac.uk\\inst$\\Kits\$\\CompGroup\\ICP\\genie_python_3\\'
    def fileContents3 = readFile basePath3 + 'LATEST_BUILD.txt'
    def pythonPath3 = basePath3 + "BUILD-$fileContents3"
    env.PYTHON3_PATH = pythonPath3
}

