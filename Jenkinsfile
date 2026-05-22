pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Deploy') {
            steps {
                sh 'chmod +x build_and_run.sh'
                sh './build_and_run.sh'
            }
        }
    }

    post {
        failure {
            sh '''
                curl -s -X POST "https://api.telegram.org/bot8891955831:AAFlT0DQtN4pednHINba87bKRya3PH_Pi9o/sendMessage" \
                    -d chat_id="5594081068" \
                    -d text="❌ DEPLOY THẤT BẠI!
Job: ${JOB_NAME}
Build: #${BUILD_NUMBER}
Commit: ${GIT_COMMIT}"
            '''
        }
    }
}