import React from 'react';
import DocumentList from '../components/document-list';
import Header from '@/app/components/header'
import { APP_INFO } from '@/config'


const DocumentsPage = () => {
    return (
        <div>
            <Header
                showInputs={false}
                title={APP_INFO.title}
            />
            <DocumentList />
        </div>
    );
};

export default DocumentsPage;